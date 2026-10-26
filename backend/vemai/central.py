import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Path, Query

from vemai.alerts import Alert, detect, is_active
from vemai.db import Database
from vemai.models import (
    CatalogStop,
    Line,
    LineDetail,
    LineSearch,
    RegionBoard,
    Stop,
    StopBoard,
    StopCatalog,
    StopSearch,
    Subscription,
    SubscriptionIn,
    Vehicle,
)
from vemai.push import PushSender, SubscriptionGone
from vemai.region import merge_boards, merge_catalogs, merge_stops, search_lines, tag_operator

log = logging.getLogger("vemai.central")
TZ = ZoneInfo("America/Sao_Paulo")
COLLECTOR_TIMEOUT_S = 10
LINE_ID = r"^[0-9a-f]{40}$"
# Itinerário e horários quase nunca mudam; as posições dos veículos nunca passam por cache.
LINE_DETAIL_TTL = timedelta(hours=6)


class CollectorError(Exception):
    def __init__(self, operator: str):
        super().__init__(operator)
        self.operator = operator


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
        self.previous: dict[str, RegionBoard] = {}

    async def cycle(self) -> None:
        now = self.clock()
        by_stop: dict[str, list[Subscription]] = {}
        for sub in self.db.list_subscriptions():
            if is_active(sub.time, now):
                by_stop.setdefault(sub.stop_id, []).append(sub)

        # Só guardamos o que foi lido por inteiro neste ciclo: um snapshot velho ou parcial geraria falsos "sumiu".
        current: dict[str, RegionBoard] = {}
        for stop_id, subs in by_stop.items():
            try:
                board = await self.fetch_board(stop_id)
            except Exception:
                log.exception("falha ao ler o ponto %s", stop_id)
                continue
            # Sem um coletor, os veículos dele somem do quadro; comparar com o anterior os daria por perdidos.
            complete = not board.unavailable
            if complete:
                current[stop_id] = board
            prev = self.previous.get(stop_id) if complete else None
            for sub in subs:
                for alert in detect(prev, board, sub):
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

    async def collector_get(
        op: str, path: str, params: dict | None = None, timeout: float = COLLECTOR_TIMEOUT_S, missing_ok: bool = False
    ):
        try:
            resp = await http.get(f"{collectors[op]}{path}", params=params, timeout=timeout)
            if missing_ok and resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CollectorError(op) from exc

    async def scatter(path: str, params: dict | None = None) -> tuple[dict, list[str]]:
        """Consulta todos os coletores da região; devolve as respostas por operadora e as que falharam."""
        outcomes = await asyncio.gather(*(collector_get(op, path, params) for op in collectors), return_exceptions=True)
        results, unavailable = {}, []
        for op, outcome in zip(collectors, outcomes):
            if isinstance(outcome, CollectorError):
                log.warning("coletor %s indisponível em %s", op, path)
                unavailable.append(op)
            elif isinstance(outcome, BaseException):
                raise outcome
            else:
                results[op] = outcome
        if not results:
            raise HTTPException(503, "nenhum coletor da região está disponível")
        return results, unavailable

    async def fetch_board(stop_id: str) -> RegionBoard:
        results, unavailable = await scatter(f"/stops/{stop_id}/board")
        boards = [tag_operator(StopBoard.model_validate(r), op) for op, r in results.items()]
        return merge_boards(stop_id, boards).model_copy(update={"unavailable": unavailable})

    async def find_line(path: str, operator: str | None) -> tuple[str, object]:
        """Pergunta à operadora indicada, ou a todas; devolve a primeira (na ordem de COLLECTORS) que conhece a linha."""
        if operator is not None and operator not in collectors:
            raise HTTPException(404, "operadora desconhecida")
        ops = [operator] if operator else list(collectors)
        outcomes = await asyncio.gather(*(collector_get(op, path, missing_ok=True) for op in ops), return_exceptions=True)
        failed = []
        for op, outcome in zip(ops, outcomes):
            if isinstance(outcome, CollectorError):
                failed.append(op)
            elif isinstance(outcome, BaseException):
                raise outcome
            elif outcome is not None:
                return op, outcome
        # A linha pode ser justamente de quem falhou, então não dá para afirmar que ela não existe.
        if failed:
            raise HTTPException(502, f"coletor indisponível: {', '.join(failed)}")
        raise HTTPException(404, "linha não encontrada")

    line_details: dict[str, tuple[datetime, LineDetail]] = {}

    def cached_line(line_id: str, operator: str | None) -> LineDetail | None:
        hit = line_details.get(line_id)
        if hit is None or clock() - hit[0] > LINE_DETAIL_TTL:
            return None
        if operator is not None and hit[1].operator != operator:
            return None
        return hit[1]

    # Lista de linhas da região, guardada como o detalhe da linha; só uma lista completa entra no cache.
    all_lines: list[tuple[datetime, list[Line]]] = []

    async def region_lines() -> tuple[list[Line], list[str]]:
        if all_lines and clock() - all_lines[0][0] <= LINE_DETAIL_TTL:
            return all_lines[0][1], []
        results, unavailable = await scatter("/lines")
        lines = [Line.model_validate(l).model_copy(update={"operator": op}) for op, r in results.items() for l in r]
        if not unavailable:
            all_lines[:] = [(clock(), lines)]
        return lines, unavailable

    monitor = Monitor(db, fetch_board, sender, clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(monitor.run_forever(interval))
        yield
        task.cancel()
        await http.aclose()

    app = FastAPI(title="Vem Aí: central", lifespan=lifespan)
    app.state.monitor = monitor

    @app.get("/api/status")
    async def status() -> list[dict]:
        async def online(op: str) -> bool:
            try:
                await collector_get(op, "/health", timeout=2)
                return True
            except CollectorError:
                return False

        states = await asyncio.gather(*(online(op) for op in collectors))
        return [{"name": op, "online": up} for op, up in zip(collectors, states)]

    @app.get("/api/stops")
    async def stops(q: str = Query(min_length=3)) -> StopSearch:
        results, unavailable = await scatter("/stops", {"q": q})
        merged = merge_stops([[Stop.model_validate(s) for s in r] for r in results.values()])
        return StopSearch(stops=merged, unavailable=unavailable)

    @app.get("/api/stops/catalog")
    async def stops_catalog() -> StopCatalog:
        results, unavailable = await scatter("/stops/catalog")
        merged = merge_catalogs([[CatalogStop.model_validate(s) for s in r] for r in results.values()])
        return StopCatalog(stops=merged, unavailable=unavailable)

    @app.get("/api/stops/{stop_id}/board")
    async def board(stop_id: str) -> RegionBoard:
        return await fetch_board(stop_id)

    @app.get("/api/lines")
    async def lines(q: str = Query(min_length=1)) -> LineSearch:
        found, unavailable = await region_lines()
        return LineSearch(lines=search_lines(found, q), unavailable=unavailable)

    @app.get("/api/lines/{line_id}")
    async def line_detail(line_id: str = Path(pattern=LINE_ID), operator: str | None = None) -> LineDetail:
        if detail := cached_line(line_id, operator):
            return detail
        op, raw = await find_line(f"/lines/{line_id}", operator)
        detail = LineDetail.model_validate(raw).model_copy(update={"operator": op})
        line_details[line_id] = (clock(), detail)
        return detail

    @app.get("/api/lines/{line_id}/vehicles")
    async def line_vehicles(line_id: str = Path(pattern=LINE_ID), operator: str | None = None) -> list[Vehicle]:
        # Quem já abriu a linha sabe a operadora; assim o polling não pergunta a todos os coletores.
        if operator is None and (known := cached_line(line_id, None)):
            operator = known.operator
        _, raw = await find_line(f"/lines/{line_id}/vehicles", operator)
        return [Vehicle.model_validate(v) for v in raw]

    @app.get("/api/vapid-public-key")
    async def vapid_public_key() -> dict[str, str]:
        return {"key": sender.public_key}

    @app.post("/api/subscriptions", status_code=201)
    async def create_subscription(body: SubscriptionIn) -> Subscription:
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
