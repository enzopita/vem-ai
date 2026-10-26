from datetime import datetime

import httpx
import pytest

from vemai.central import TZ, create_app
from vemai.db import Database
from vemai.push import SubscriptionGone

pytestmark = pytest.mark.anyio

LINE = {"id": "aaa", "label": "184"}


def board_json(*preds):
    return {
        "stop_id": "9306",
        "predictions": [{"line": LINE, "vehicle": v, "eta_min": e} for v, e in preds],
        "other_lines": [],
    }


class FakeCollector:
    def __init__(self):
        self.board = board_json(("4430", 5))
        self.down = False
        self.down_hosts: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.down or request.url.host in self.down_hosts:
            raise httpx.ConnectError("offline")
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/stops":
            return httpx.Response(200, json=[{"id": "9306", "name": "AV. X"}])
        return httpx.Response(200, json=self.board)


class StubSender:
    public_key = "chave-publica"

    def __init__(self):
        self.sent = []
        self.gone = False

    async def send(self, sub, title, body, url="/"):
        if self.gone:
            raise SubscriptionGone
        self.sent.append((sub.id, title, body))


SUB = {
    "endpoint": "https://push.example/abc",
    "keys": {"p256dh": "p", "auth": "a"},
    "operator": "piracicabana",
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


async def test_operators_reports_online_state(env):
    client, _, collector, *_ = env
    assert (await client.get("/api/operators")).json() == [
        {"name": "piracicabana", "online": True},
        {"name": "brmobilidadebs", "online": True},
    ]
    collector.down = True
    assert not any(o["online"] for o in (await client.get("/api/operators")).json())


async def test_proxy_stops_board_and_error_codes(env):
    client, _, collector, *_ = env
    assert (await client.get("/api/operators/piracicabana/stops", params={"q": "cons"})).json()[0]["id"] == "9306"
    assert (await client.get("/api/operators/piracicabana/stops/9306/board")).json()["stop_id"] == "9306"
    assert (await client.get("/api/operators/nope/stops", params={"q": "cons"})).status_code == 404
    assert (await client.get("/api/operators/piracicabana/stops", params={"q": "co"})).status_code == 422
    collector.down = True
    assert (await client.get("/api/operators/piracicabana/stops/9306/board")).status_code == 503


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
    assert (await client.post("/api/subscriptions", json={**SUB, "operator": "x"})).status_code == 422


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
    collector.board = board_json(("4430", 8))
    await monitor.cycle()
    assert sender.sent == []
    collector.board = board_json()
    await monitor.cycle()
    assert len(sender.sent) == 1 and "GPS" in sender.sent[0][2]


async def test_monitor_ignores_inactive_subscriptions(env):
    client, monitor, _, sender, now = env
    await client.post("/api/subscriptions", json=SUB)
    now["value"] = datetime(2026, 5, 4, 12, 0, tzinfo=TZ)
    await monitor.cycle()
    assert sender.sent == []


async def test_one_failing_collector_does_not_stop_the_others(env):
    client, monitor, collector, sender, _ = env
    await client.post("/api/subscriptions", json={**SUB, "operator": "brmobilidadebs", "stop_id": "1"})
    await client.post("/api/subscriptions", json=SUB)
    collector.down_hosts.add("c2")
    await monitor.cycle()
    assert len(sender.sent) == 1
