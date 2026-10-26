from datetime import datetime

import httpx
import pytest

from vemai.central import TZ, create_app
from vemai.db import Database
from vemai.push import SubscriptionGone

pytestmark = pytest.mark.anyio

LINE = {"id": "aaa", "label": "184"}


LINE2 = {"id": "bbb", "label": "956"}


def board_json(*preds, line=LINE):
    return {
        "stop_id": "9306",
        "predictions": [{"line": line, "vehicle": v, "eta_min": e} for v, e in preds],
        "other_lines": [],
    }


class FakeCollector:
    """Dois sites da mesma região: ids de ponto compartilhados, linhas diferentes por host."""

    def __init__(self):
        self.boards = {"c1": board_json(("4430", 5)), "c2": board_json(("9001", 7), line=LINE2)}
        self.stops = {"c1": [{"id": "9306", "name": "AV. X"}], "c2": [{"id": "9306", "name": "AV. X"}, {"id": "1", "name": "RUA A"}]}
        self.down_hosts: set[str] = set()

    @property
    def down(self):
        return self.down_hosts == {"c1", "c2"}

    @down.setter
    def down(self, value: bool):
        self.down_hosts = {"c1", "c2"} if value else set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host in self.down_hosts:
            raise httpx.ConnectError("offline")
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/stops":
            return httpx.Response(200, json=self.stops[host])
        return httpx.Response(200, json=self.boards[host])


class StubSender:
    public_key = "chave-publica"

    def __init__(self):
        self.sent = []
        self.gone = False

    async def send(self, sub, title, body):
        if self.gone:
            raise SubscriptionGone
        self.sent.append((sub.id, title, body))


SUB = {
    "endpoint": "https://push.example/abc",
    "keys": {"p256dh": "p", "auth": "a"},
    "stop_id": "9306",
    "stop_name": "AV. X",
    "line_id": "aaa",
    "line_label": "184",
    "time": "08:00",
    "lead_min": 10,
}


@pytest.fixture
def env(tmp_path):
    collector, sender = FakeCollector(), StubSender()
    now = {"value": datetime(2026, 5, 4, 8, 0, tzinfo=TZ)}
    app = create_app(
        db=Database(str(tmp_path / "t.db")),
        collectors={"piracicabana": "http://c1", "brmobilidadebs": "http://c2"},
        sender=sender,
        http=httpx.AsyncClient(transport=httpx.MockTransport(collector)),
        monitor_interval_s=30,
        clock=lambda: now["value"],
    )
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    return client, app.state.monitor, collector, sender, now


async def test_status_reports_online_state_per_collector(env):
    client, _, collector, *_ = env
    assert (await client.get("/api/status")).json() == [
        {"name": "piracicabana", "online": True},
        {"name": "brmobilidadebs", "online": True},
    ]
    collector.down_hosts = {"c2"}
    assert [o["online"] for o in (await client.get("/api/status")).json()] == [True, False]
    collector.down = True
    assert not any(o["online"] for o in (await client.get("/api/status")).json())


async def test_stops_search_unions_the_region(env):
    client, *_ = env
    body = (await client.get("/api/stops", params={"q": "cons"})).json()
    assert [s["id"] for s in body["stops"]] == ["9306", "1"]
    assert len(body["stops"]) == 2
    assert body["unavailable"] == []
    assert (await client.get("/api/stops", params={"q": "co"})).status_code == 422


async def test_board_mixes_lines_of_every_operator(env):
    client, *_ = env
    body = (await client.get("/api/stops/9306/board")).json()
    assert [(p["line"]["label"], p["eta_min"]) for p in body["predictions"]] == [("184", 5), ("956", 7)]
    assert body["unavailable"] == []


async def test_one_collector_down_gives_partial_result(env):
    client, _, collector, *_ = env
    collector.down_hosts = {"c2"}
    board = await client.get("/api/stops/9306/board")
    assert board.status_code == 200
    assert board.json()["unavailable"] == ["brmobilidadebs"]
    assert [p["line"]["label"] for p in board.json()["predictions"]] == ["184"]
    stops = (await client.get("/api/stops", params={"q": "cons"})).json()
    assert stops["unavailable"] == ["brmobilidadebs"]
    assert [s["id"] for s in stops["stops"]] == ["9306"]


async def test_all_collectors_down_is_503(env):
    client, _, collector, *_ = env
    collector.down = True
    assert (await client.get("/api/stops/9306/board")).status_code == 503
    assert (await client.get("/api/stops", params={"q": "cons"})).status_code == 503


async def test_vapid_public_key(env):
    client, *_ = env
    assert (await client.get("/api/vapid-public-key")).json() == {"key": "chave-publica"}


async def test_subscription_create_list_delete(env):
    client, *_ = env
    created = await client.post("/api/subscriptions", json=SUB)
    assert created.status_code == 201
    sub_id = created.json()["id"]

    listed = await client.get("/api/subscriptions", params={"endpoint": SUB["endpoint"]})
    assert [s["id"] for s in listed.json()] == [sub_id]
    assert (await client.get("/api/subscriptions", params={"endpoint": "outro"})).json() == []

    owner = {"endpoint": SUB["endpoint"]}
    assert (await client.delete(f"/api/subscriptions/{sub_id}", params={"endpoint": "outro"})).status_code == 404
    assert (await client.delete(f"/api/subscriptions/{sub_id}", params=owner)).status_code == 204
    assert (await client.delete(f"/api/subscriptions/{sub_id}", params=owner)).status_code == 404


async def test_subscription_validation(env):
    client, *_ = env
    assert (await client.post("/api/subscriptions", json={**SUB, "time": "8h"})).status_code == 422
    assert (await client.post("/api/subscriptions", json={**SUB, "lead_min": 31})).status_code == 422


async def test_test_push_endpoint_sends_and_cleans_gone_subscriptions(env):
    client, _, _, sender, _ = env
    sub_id = (await client.post("/api/subscriptions", json=SUB)).json()["id"]
    assert (await client.post(f"/api/subscriptions/{sub_id}/test", params={"endpoint": SUB["endpoint"]})).status_code == 204
    assert [s[0] for s in sender.sent] == [sub_id]
    sender.gone = True
    assert (await client.post(f"/api/subscriptions/{sub_id}/test", params={"endpoint": SUB["endpoint"]})).status_code == 410
    assert (await client.get("/api/subscriptions", params={"endpoint": SUB["endpoint"]})).json() == []


async def test_monitor_sends_one_push_per_vehicle_kind_and_day(env):
    client, monitor, _, sender, now = env
    sub_id = (await client.post("/api/subscriptions", json=SUB)).json()["id"]

    await monitor.cycle()
    await monitor.cycle()
    assert [s[0] for s in sender.sent] == [sub_id]
    assert "4430" in sender.sent[0][2]

    now["value"] = datetime(2026, 5, 5, 8, 0, tzinfo=TZ)
    await monitor.cycle()
    assert len(sender.sent) == 2


async def test_monitor_notifies_when_vehicle_vanishes(env):
    client, monitor, collector, sender, _ = env
    await client.post("/api/subscriptions", json={**SUB, "lead_min": 1})
    collector.boards["c1"] = board_json(("4430", 8))
    await monitor.cycle()
    assert sender.sent == []
    collector.boards["c1"] = board_json()
    await monitor.cycle()
    assert len(sender.sent) == 1 and "GPS" in sender.sent[0][2]


async def test_monitor_ignores_inactive_subscriptions(env):
    client, monitor, _, sender, now = env
    await client.post("/api/subscriptions", json=SUB)
    now["value"] = datetime(2026, 5, 4, 12, 0, tzinfo=TZ)
    await monitor.cycle()
    assert sender.sent == []


async def test_one_failing_stop_does_not_stop_the_others(env):
    client, monitor, collector, sender, _ = env
    await client.post("/api/subscriptions", json={**SUB, "stop_id": "1", "line_id": "zzz"})
    await client.post("/api/subscriptions", json=SUB)
    real = monitor.fetch_board

    async def flaky(stop_id):
        if stop_id == "1":
            raise RuntimeError("boom")
        return await real(stop_id)

    monitor.fetch_board = flaky
    await monitor.cycle()
    assert len(sender.sent) == 1



async def test_monitor_partial_board_does_not_fake_vanished_but_still_alerts_arriving(env):
    client, monitor, collector, sender, _ = env
    await client.post("/api/subscriptions", json={**SUB, "line_id": "bbb", "line_label": "956", "lead_min": 5})
    await client.post("/api/subscriptions", json={**SUB, "lead_min": 5})
    collector.boards["c2"] = board_json(("9001", 10), line=LINE2)
    collector.boards["c1"] = board_json(("4430", 20))
    await monitor.cycle()
    assert sender.sent == []

    collector.down_hosts = {"c2"}
    collector.boards["c1"] = board_json(("4430", 4))
    await monitor.cycle()
    assert len(sender.sent) == 1 and "4430" in sender.sent[0][2]
    assert not any("GPS" in s[2] for s in sender.sent)

    collector.down_hosts = set()
    collector.boards["c2"] = board_json(("9001", 8), line=LINE2)
    await monitor.cycle()
    assert not any("GPS" in s[2] for s in sender.sent)

    collector.boards["c2"] = board_json(line=LINE2)
    await monitor.cycle()
    assert sum("GPS" in s[2] for s in sender.sent) == 1
