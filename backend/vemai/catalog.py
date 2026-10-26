"""Catálogo de todos os pontos da operadora, com código e coordenada.

O site não tem busca por proximidade nem lista de pontos com código. O mapa de cada linha dá nome e
coordenada sem código; a busca por texto dá código e nome sem coordenada; o mapa centrado num código
dá a coordenada dele. O catálogo cruza os três.
"""

import asyncio
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from vemai.models import CatalogStop, Stop

log = logging.getLogger("vemai.catalog")

DAY_S = 24 * 3600
RETRY_S = 3600
CONCURRENCY = 3
DELAY_S = 0.3

_PARENTHETICAL = re.compile(r"\([^)]*\)")
_GAP = re.compile(r"\s{2,}")


class CatalogSource(Protocol):
    async def list_lines(self) -> list[str]: ...
    async def line_stop_names(self, line_id: str) -> list[str]: ...
    async def search_stops(self, query: str) -> list[Stop]: ...
    async def stop_location(self, stop_id: str, line_id: str) -> tuple[float, float] | None: ...


def normalize(text: str) -> str:
    return " ".join(text.split()).upper()


def street_of(name: str) -> str:
    """'AV. ANA COSTA, 120 (P7)' e 'PRAÇA GAGO COUTINHO - B' viram o logradouro, que a busca acha por trecho."""
    street = _PARENTHETICAL.sub("  ", name).split(",", 1)[0].split(" - ", 1)[0]
    # A busca compara os espaços ao pé da letra ('PRAÇA  GAGO' não casa com 'PRAÇA GAGO'), então o termo
    # tem de ser um trecho literal do nome: o pedaço mais longo entre espaços duplos.
    return max((part.strip() for part in _GAP.split(street)), key=len)


def search_terms(names: Iterable[str]) -> list[str]:
    streets = sorted({s for s in map(street_of, names) if len(s) >= 3}, key=lambda s: (len(s), s))
    # A busca casa por trecho do nome, então um termo que contém outro já buscado só repetiria resultados.
    terms: list[str] = []
    for street in streets:
        if not any(term in street for term in terms):
            terms.append(street)
    return terms


async def _gently[T](calls: list[tuple[str, Callable[[], Awaitable[T]]]], concurrency: int, delay_s: float) -> list[T | None]:
    """Roda as consultas com poucas em paralelo e uma pausa entre elas; uma falha vira None e não derruba as outras."""
    sem = asyncio.Semaphore(concurrency)

    async def one(label: str, call: Callable[[], Awaitable[T]]) -> T | None:
        async with sem:
            try:
                return await call()
            except Exception as exc:
                log.warning("falha em %s: %s", label, exc)
                return None
            finally:
                await asyncio.sleep(delay_s)

    return await asyncio.gather(*(one(label, call) for label, call in calls))


async def build_catalog(source: CatalogSource, concurrency: int = CONCURRENCY, delay_s: float = DELAY_S) -> list[CatalogStop]:
    lines = await source.list_lines()
    if not lines:
        return []
    log.info("catálogo: %d linhas", len(lines))

    per_line = await _gently(
        [(f"mapa da linha {line}", lambda line=line: source.line_stop_names(line)) for line in lines], concurrency, delay_s
    )
    names = {name for found in per_line if found for name in found}
    terms = search_terms(names)
    log.info("catálogo: %d nomes de ponto nos mapas, %d termos de busca", len(names), len(terms))

    found = await _gently([(f"busca {term!r}", lambda term=term: source.search_stops(term)) for term in terms], concurrency, delay_s)
    by_id: dict[str, Stop] = {}
    for stops in found:
        for stop in stops or []:
            by_id.setdefault(stop.id, stop)
    unmatched = {normalize(n) for n in names} - {normalize(s.name) for s in by_id.values()}
    log.info(
        "catálogo: %d códigos encontrados; %d nomes dos mapas sem código %s", len(by_id), len(unmatched), sorted(unmatched)[:5]
    )

    # O mapa centra no ponto pedido mesmo que a linha não passe por ele, então qualquer linha serve.
    any_line = lines[0]
    ids = sorted(by_id)
    located = await _gently(
        [(f"coordenada do ponto {i}", lambda i=i: source.stop_location(i, any_line)) for i in ids], concurrency, delay_s
    )
    catalog = [
        CatalogStop(id=i, name=by_id[i].name, lat=where[0], lng=where[1])
        for i, where in zip(ids, located)
        if where and where != (0.0, 0.0)
    ]
    log.info("catálogo: %d pontos com coordenada", len(catalog))
    return catalog


def default_path(base_url: str) -> Path:
    # Os coletores rodam no mesmo diretório; o host separa o arquivo de cada operadora.
    return Path(os.environ.get("CATALOG_PATH") or f"data/catalog-{urlparse(base_url).hostname}.json")


class _CatalogFile(BaseModel):
    built_at: float
    stops: list[CatalogStop]


class Catalog:
    """Mantém o catálogo em arquivo e o reconstrói a cada max_age_s; até lá, serve o último que deu certo."""

    def __init__(
        self,
        path: Path,
        build: Callable[[], Awaitable[list[CatalogStop]]],
        max_age_s: float = DAY_S,
        retry_s: float = RETRY_S,
        clock: Callable[[], float] = time.time,
    ):
        self.path, self.build, self.max_age_s, self.retry_s, self.clock = path, build, max_age_s, retry_s, clock
        self.stops: list[CatalogStop] = []
        self.built_at: float | None = None

    def load(self) -> None:
        try:
            saved = _CatalogFile.model_validate_json(self.path.read_bytes())
        except FileNotFoundError:
            return
        except (OSError, ValidationError):
            log.exception("catálogo em %s ilegível; será reconstruído", self.path)
            return
        self.stops, self.built_at = saved.stops, saved.built_at
        log.info("catálogo: %d pontos lidos de %s", len(self.stops), self.path)

    def seconds_until_stale(self) -> float:
        return 0.0 if self.built_at is None else self.built_at + self.max_age_s - self.clock()

    async def refresh(self) -> bool:
        started = self.clock()
        try:
            stops = await self.build()
        except Exception:
            log.exception("falha ao montar o catálogo")
            return False
        if not stops:
            # Um catálogo vazio quase sempre é o site fora do ar; não vale sobrescrever o último bom.
            log.warning("catálogo montado sem pontos; mantendo o anterior")
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(_CatalogFile(built_at=started, stops=stops).model_dump_json(), encoding="utf-8")
        os.replace(tmp, self.path)
        self.stops, self.built_at = stops, started
        log.info("catálogo: %d pontos salvos em %s (%.0f s)", len(stops), self.path, self.clock() - started)
        return True

    async def run_forever(self) -> None:
        self.load()
        while True:
            wait = self.seconds_until_stale()
            if wait > 0:
                await asyncio.sleep(wait)
            elif not await self.refresh():
                await asyncio.sleep(self.retry_s)
