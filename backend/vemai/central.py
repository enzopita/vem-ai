import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query

from vemai.alerts import Alert, detect, is_active
from vemai.db import Database
from vemai.models import StopBoard, Subscription, SubscriptionIn
from vemai.push import PushSender, SubscriptionGone

log = logging.getLogger("vemai.central")
TZ = ZoneInfo("America/Sao_Paulo")


def parse_collectors(spec: str) -> dict[str, str]:
    return dict(pair.split("=", 1) for pair in spec.split(",") if pair.strip())


def describe(alert: Alert, stop_name: str) -> tuple[str, str]:
    if alert.kind == "arriving":
        when = "está chegando" if alert.eta_min == 0 else f"chega em {alert.eta_min} min"
        return f"Linha {alert.line_label} a caminho", f"O veículo {alert.vehicle} {when} ao ponto {stop_name}."
    return (
        f"Linha {alert.line_label} sumiu do rastreamento",
        f"O veículo {alert.vehicle} desapareceu (provável perda de sinal de GPS). "
        f"Última previsão: {alert.eta_min} min para {stop_name}.",
    )


class Monitor:
    def __init__(self, db: Database, fetch_board: Callable, sender: PushSender, clock: Callable[[], datetime]):
        self.db, self.fetch_board, self.sender, self.clock = db, fetch_board, sender, clock
        self.previous: dict[tuple[str, str], StopBoard] = {}

    async def cycle(self) -> None:
        now = self.clock()
        by_stop: dict[tuple[str, str], list[Subscription]] = {}
        for sub in self.db.list_subscriptions():
            if is_active(sub.time, now):
                by_stop.setdefault((sub.operator, sub.stop_id), []).append(sub)

        # Só guardamos o que foi lido neste ciclo: um snapshot velho geraria falsos "sumiu".
        current: dict[tuple[str, str], StopBoard] = {}
        for key, subs in by_stop.items():
            try:
                board = await self.fetch_board(*key)
            except Exception:
                log.exception("falha ao ler o ponto %s", key)
                continue
            current[key] = board
            for sub in subs:
                for alert in detect(self.previous.get(key), board, sub):
                    if self.db.record_notification(sub.id, alert.vehicle, alert.kind, now.date().isoformat()):
                        await self._push(sub, *describe(alert, sub.stop_name))
        self.previous = current

    async def _push(self, sub: Subscription, title: str, body: str) -> None:
        try:
            await self.sender.send(sub, title, body)
        except SubscriptionGone:
            self.db.delete_subscription(sub.id)
        except Exception:
            log.exception("falha ao enviar push da inscrição %s", sub.id)

    async def run_forever(self, interval_s: float) -> None:
        while True:
            try:
                await self.cycle()
            except Exception:
                log.exception("falha no ciclo do monitor")
            await asyncio.sleep(interval_s)


def create_app(
    db: Database | None = None,
    collectors: dict[str, str] | None = None,
    sender: PushSender | None = None,
    http: httpx.AsyncClient | None = None,
    monitor_interval_s: float | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(TZ),
) -> FastAPI:
    db = db or Database()
    collectors = collectors if collectors is not None else parse_collectors(os.environ.get("COLLECTORS", ""))
    sender = sender or PushSender()
    http = http or httpx.AsyncClient(timeout=15)
    interval = monitor_interval_s or float(os.environ.get("MONITOR_INTERVAL_S", "30"))

    async def collector_get(op: str, path: str, params: dict | None = None, timeout: float = 15):
        if op not in collectors:
            raise HTTPException(404, f"operadora desconhecida: {op}")
        try:
            resp = await http.get(f"{collectors[op]}{path}", params=params, timeout=timeout)
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"coletor da operadora {op} indisponível") from exc
        if resp.is_error:
            raise HTTPException(resp.status_code, resp.json().get("detail", "erro no coletor"))
        return resp.json()

    async def fetch_board(op: str, stop_id: str) -> StopBoard:
        return StopBoard.model_validate(await collector_get(op, f"/stops/{stop_id}/board"))

    monitor = Monitor(db, fetch_board, sender, clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(monitor.run_forever(interval))
        yield
        task.cancel()
        await http.aclose()

    app = FastAPI(title="Vem Aí: central", lifespan=lifespan)
    app.state.monitor = monitor

    @app.get("/api/operators")
    async def operators() -> list[dict]:
        async def online(op: str) -> bool:
            try:
                await collector_get(op, "/health", timeout=2)
                return True
            except HTTPException:
                return False

        states = await asyncio.gather(*(online(op) for op in collectors))
        return [{"name": op, "online": up} for op, up in zip(collectors, states)]

    @app.get("/api/operators/{op}/stops")
    async def stops(op: str, q: str = Query(min_length=3)):
        return await collector_get(op, "/stops", {"q": q})

    @app.get("/api/operators/{op}/stops/{stop_id}/board")
    async def board(op: str, stop_id: str):
        return await collector_get(op, f"/stops/{stop_id}/board")

    @app.get("/api/vapid-public-key")
    async def vapid_public_key() -> dict[str, str]:
        return {"key": sender.public_key}

    @app.post("/api/subscriptions", status_code=201)
    async def create_subscription(body: SubscriptionIn) -> Subscription:
        if body.operator not in collectors:
            raise HTTPException(422, f"operadora desconhecida: {body.operator}")
        return db.add_subscription(body)

    @app.get("/api/subscriptions")
    async def list_subscriptions(endpoint: str) -> list[Subscription]:
        return db.list_subscriptions(endpoint)

    # O endpoint de push só é conhecido pelo navegador que criou o alerta, por isso serve de prova de posse.
    def owned_subscription(sub_id: int, endpoint: str) -> Subscription:
        sub = db.get_subscription(sub_id)
        if sub is None or sub.endpoint != endpoint:
            raise HTTPException(404, "alerta não encontrado")
        return sub

    @app.delete("/api/subscriptions/{sub_id}", status_code=204)
    async def delete_subscription(sub_id: int, endpoint: str) -> None:
        db.delete_subscription(owned_subscription(sub_id, endpoint).id)

    @app.post("/api/subscriptions/{sub_id}/test", status_code=204)
    async def test_subscription(sub_id: int, endpoint: str) -> None:
        sub = owned_subscription(sub_id, endpoint)
        try:
            await sender.send(
                sub, "Vem Aí: teste", f"Alerta da linha {sub.line_label} no ponto {sub.stop_name} funcionando."
            )
        except SubscriptionGone:
            db.delete_subscription(sub.id)
            raise HTTPException(410, "o navegador cancelou esta inscrição") from None

    return app
