import pytest

from vemai.catalog import Catalog, build_catalog, search_terms
from vemai.models import CatalogStop, Stop
from vemai.scraper import UpstreamError

pytestmark = pytest.mark.anyio


def test_search_terms_keep_the_street_once():
    names = [
        "AV. ANA COSTA, 120",
        "AV. ANA COSTA, 455",
        "AV.  ANA COSTA (PRAÇA BELMIRO RIBEIRO)",
        "PRAÇA GAGO COUTINHO - C",
        "PRAÇA GAGO COUTINHO - B",
        "TERMINAL VALONGO (PLATAFORMA D)",
        "AB, 12",
    ]
    assert sorted(search_terms(names)) == ["ANA COSTA", "PRAÇA GAGO COUTINHO", "TERMINAL VALONGO"]


def test_search_terms_skip_streets_already_covered_by_a_shorter_term():
    assert search_terms(["AV. REI ALBERTO I, 117", "AV. REI ALBERTO I SENAI, 2"]) == ["AV. REI ALBERTO I"]


class FakeSite:
    """Uma operadora pequena: duas linhas, busca por trecho do nome, coordenada por código."""

    def __init__(self):
        self.stops = {
            "9306": ("AV. CONSELHEIRO NÉBIAS, 107", (-23.93749, -46.32090)),
            "9305": ("AV. CONSELHEIRO NÉBIAS, 187", (-23.93800, -46.32100)),
            "4096": ("AV. ANA COSTA (PRAÇA BELMIRO RIBEIRO)", (-23.94364, -46.33011)),
            "4064": ("PRAÇA  GAGO COUTINHO - B", (-23.98800, -46.29800)),
            "7000": ("RUA SEM GPS, 1", (0.0, 0.0)),
            "7001": ("RUA SEM MAPA, 1", None),
            "7002": ("RUA INSTÁVEL, 1", (-23.9, -46.3)),
        }
        self.lines = {
            "l1": ["AV. CONSELHEIRO NÉBIAS, 107", "AV. CONSELHEIRO NÉBIAS, 187", "RUA SEM GPS, 1", "PRAÇA  GAGO COUTINHO - B"],
            "l2": ["AV. ANA COSTA (PRAÇA BELMIRO RIBEIRO)", "RUA SEM MAPA, 1", "RUA INSTÁVEL, 1"],
        }
        self.searches: list[str] = []

    async def list_lines(self):
        return list(self.lines)

    async def line_stop_names(self, line_id):
        return self.lines[line_id]

    async def search_stops(self, query):
        self.searches.append(query)
        return [Stop(id=i, name=name) for i, (name, _) in self.stops.items() if query in name]

    async def stop_location(self, stop_id, line_id):
        if stop_id == "7002":
            raise UpstreamError("tempo esgotado")
        return self.stops[stop_id][1]


async def test_build_catalog_correlates_codes_and_coordinates():
    site = FakeSite()
    catalog = await build_catalog(site, delay_s=0)
    assert catalog == [
        CatalogStop(id="4064", name="PRAÇA  GAGO COUTINHO - B", lat=-23.988, lng=-46.298),
        CatalogStop(id="4096", name="AV. ANA COSTA (PRAÇA BELMIRO RIBEIRO)", lat=-23.94364, lng=-46.33011),
        CatalogStop(id="9305", name="AV. CONSELHEIRO NÉBIAS, 187", lat=-23.938, lng=-46.321),
        CatalogStop(id="9306", name="AV. CONSELHEIRO NÉBIAS, 107", lat=-23.93749, lng=-46.3209),
    ]
    assert len(site.searches) < len(site.stops)


async def test_build_catalog_skips_a_failed_search():
    site = FakeSite()
    real = site.search_stops

    async def flaky(query):
        if "ANA COSTA" in query:
            raise UpstreamError("fora do ar")
        return await real(query)

    site.search_stops = flaky
    assert [s.id for s in await build_catalog(site, delay_s=0)] == ["4064", "9305", "9306"]


STOP = CatalogStop(id="1", name="RUA A", lat=-23.9, lng=-46.3)


class Builds:
    def __init__(self, *results):
        self.results, self.calls = list(results), 0

    async def __call__(self):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


async def test_catalog_survives_restart_without_rebuilding(tmp_path):
    path, now = tmp_path / "c.json", [1000.0]
    first = Catalog(path, Builds([STOP]), max_age_s=100, clock=lambda: now[0])
    assert first.seconds_until_stale() <= 0
    assert await first.refresh()

    now[0] = 1050.0
    builds = Builds()
    restarted = Catalog(path, builds, max_age_s=100, clock=lambda: now[0])
    restarted.load()
    assert restarted.stops == [STOP]
    assert restarted.seconds_until_stale() == 50
    assert builds.calls == 0


async def test_failed_or_empty_rebuild_keeps_the_last_good_catalog(tmp_path):
    path = tmp_path / "c.json"
    catalog = Catalog(path, Builds([STOP], [], UpstreamError("fora do ar")))
    assert await catalog.refresh()
    assert not await catalog.refresh()
    assert not await catalog.refresh()
    assert catalog.stops == [STOP]

    reloaded = Catalog(path, Builds())
    reloaded.load()
    assert reloaded.stops == [STOP]


async def test_unreadable_file_means_rebuild(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{meio arquivo")
    catalog = Catalog(path, Builds())
    catalog.load()
    assert catalog.stops == []
    assert catalog.seconds_until_stale() <= 0
