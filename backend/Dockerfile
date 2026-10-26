# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
# Bytecode compilado na imagem e cópia em vez de links: o cache do uv fica fora da camada final.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependências antes do código: mudar o código não reinstala nada, e o cache do uv sobrevive entre builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project
COPY pyproject.toml uv.lock ./
COPY vemai ./vemai
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd --system --uid 10001 --home-dir /app vemai && mkdir -p /app/data && chown vemai /app/data
WORKDIR /app
# O scraper acha os certificados em ../certs a partir do pacote, então o código fica em /app/vemai.
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/vemai ./vemai
COPY certs ./certs
# A imagem não depende do modo dos arquivos de origem (uma cópia local com 600 deixaria o código ilegível).
RUN chmod -R a+rX /app/vemai /app/certs
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER vemai
EXPOSE 8000
CMD ["uvicorn", "vemai.central:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
