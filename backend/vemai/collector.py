import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path, Query

from vemai.models import Stop, StopBoard
from vemai.scraper import OperatorClient, UpstreamError


def create_app(client: OperatorClient | None = None) -> FastAPI:
    client = client or OperatorClient(os.environ["OPERATOR_BASE_URL"])

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await client.aclose()

    app = FastAPI(title="Vem Aí: coletor", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/stops")
    async def stops(q: str = Query(min_length=3)) -> list[Stop]:
        try:
            return await client.search_stops(q)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/stops/{stop_id}/board")
    async def board(stop_id: str = Path(pattern=r"^\d+$")) -> StopBoard:
        try:
            return await client.board(stop_id)
        except UpstreamError as exc:
            raise HTTPException(502, str(exc)) from exc

    return app
