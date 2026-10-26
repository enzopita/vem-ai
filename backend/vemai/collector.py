import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path as FilePath

from fastapi import FastAPI, HTTPException, Path, Query

from vemai.catalog import Catalog, build_catalog, default_path
from vemai.models import CatalogStop, Line, LineDetail, Stop, StopBoard, Vehicle
from vemai.scraper import OperatorClient, UpstreamError

LINE_ID = r"^[0-9a-f]{40}$"


def _show_catalog_progress() -> None:
    # O uvicorn só configura os próprios loggers; sem um handler aqui o progresso do catálogo (INFO) some.
    log = logging.getLogger("vemai.catalog")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)


def create_app(client: OperatorClient | None = None, catalog_path: FilePath | None = None) -> FastAPI:
    client = client or OperatorClient(os.environ["OPERATOR_BASE_URL"])
    _show_catalog_progress()
    catalog = Catalog(catalog_path or default_path(os.environ["OPERATOR_BASE_URL"]), lambda: build_catalog(client))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(catalog.run_forever())
        yield
        task.cancel()
        await client.aclose()

    app = FastAPI(title="Vem Aí: coletor", lifespan=lifespan)
    app.state.catalog = catalog

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/stops")
    async def stops(q: str = Query(min_length=3)) -> list[Stop]:
        try:
            return await client.search_stops(q)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/stops/catalog")
    async def stops_catalog() -> list[CatalogStop]:
        return catalog.stops

    @app.get("/stops/{stop_id}/board")
    async def board(stop_id: str = Path(pattern=r"^\d+$")) -> StopBoard:
        try:
            return await client.board(stop_id)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/lines")
    async def lines() -> list[Line]:
        try:
            return await client.lines()
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/lines/{line_id}")
    async def line_detail(line_id: str = Path(pattern=LINE_ID)) -> LineDetail:
        try:
            detail = await client.line_detail(line_id)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc
        if detail is None:
            raise HTTPException(404, "linha desconhecida nesta operadora")
        return detail

    @app.get("/lines/{line_id}/vehicles")
    async def vehicles(line_id: str = Path(pattern=LINE_ID)) -> list[Vehicle]:
        try:
            found = await client.vehicles(line_id)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc
        if found is None:
            raise HTTPException(404, "linha desconhecida nesta operadora")
        return found

    return app
