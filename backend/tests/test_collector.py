import asyncio
import time

import httpx
import pytest

from vemai.collector import create_app
from vemai.models import CatalogStop, LineDetail, Stop, StopBoard, Vehicle
from vemai.scraper import UpstreamError

pytestmark = pytest.mark.anyio

KNOWN_LINE = "2ecd397b94205c2a35f33d0970bf53d15a548a0c"
OTHER_LINE = "c9e8f2f3b02a56c2c3360ac8b1834c1da3f90412"
DETAIL = LineDetail(id=KNOWN_LINE, label="CIRCULAR 007", description="Centro", directions=[], stops=[], schedules=[])
BUS = Vehicle(prefix="4407", driver="ALEX", lat=-23.97, lng=-46.32, direction="volta", seen_at="12:07:17")


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail

    async def search_stops(self, query):
        if self.fail:
            raise UpstreamError("fora do ar")
        return [Stop(id="9306", name="AV. X")]

    async def board(self, stop_id):
        if self.fail:
            raise UpstreamError("fora do ar")
        return StopBoard(stop_id=stop_id, predictions=[], other_lines=[])

    async def line_detail(self, line_id):
        if self.fail:
            raise UpstreamError("fora do ar")
        return DETAIL if line_id == KNOWN_LINE else None

    async def vehicles(self, line_id):
        if self.fail:
            raise UpstreamError("fora do ar")
        return [BUS] if line_id == KNOWN_LINE else None

    async def aclose(self):
        pass


def http(fail=False, catalog_path=None):
    app = create_app(FakeClient(fail), catalog_path=catalog_path or "sem-catalogo.json")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_search_requires_three_characters():
    async with http() as c:
        assert (await c.get("/stops", params={"q": "co"})).status_code == 422
        resp = await c.get("/stops", params={"q": "cons"})
    assert resp.json() == [{"id": "9306", "name": "AV. X"}]


async def test_board_returns_stop_board():
    async with http() as c:
        resp = await c.get("/stops/9306/board")
    assert resp.json()["stop_id"] == "9306"


async def test_upstream_failure_is_502_with_message():
    async with http(fail=True) as c:
        resp = await c.get("/stops/9306/board")
    assert resp.status_code == 502
    assert "fora do ar" in resp.json()["detail"]


async def test_catalog_route_serves_the_saved_catalog(tmp_path):
    path = tmp_path / "catalog.json"
    stop = CatalogStop(id="4096", name="AV. ANA COSTA", lat=-23.94, lng=-46.33)
    path.write_text(f'{{"built_at": {time.time()}, "stops": [{stop.model_dump_json()}]}}')
    app = create_app(FakeClient(), catalog_path=path)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/stops/catalog")
    assert resp.json() == [stop.model_dump()]


async def test_line_detail_route():
    async with http() as c:
        found = await c.get(f"/lines/{KNOWN_LINE}")
        missing = await c.get(f"/lines/{OTHER_LINE}")
        malformed = await c.get("/lines/007")
    assert found.json()["label"] == "CIRCULAR 007"
    assert missing.status_code == 404
    assert malformed.status_code == 422


async def test_vehicles_route():
    async with http() as c:
        found = await c.get(f"/lines/{KNOWN_LINE}/vehicles")
        missing = await c.get(f"/lines/{OTHER_LINE}/vehicles")
    assert found.json() == [BUS.model_dump()]
    assert missing.status_code == 404


async def test_line_routes_upstream_failure_is_502():
    async with http(fail=True) as c:
        assert (await c.get(f"/lines/{KNOWN_LINE}")).status_code == 502
        assert (await c.get(f"/lines/{KNOWN_LINE}/vehicles")).status_code == 502
