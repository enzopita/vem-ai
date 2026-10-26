import httpx
import pytest

from vemai.collector import create_app
from vemai.models import Stop, StopBoard
from vemai.scraper import UpstreamError

pytestmark = pytest.mark.anyio


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

    async def aclose(self):
        pass


def http(fail=False):
    app = create_app(FakeClient(fail))
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
