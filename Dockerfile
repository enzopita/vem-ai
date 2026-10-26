FROM node:24-slim AS web
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml web/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY web ./
RUN pnpm build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY vemai ./vemai
COPY certs ./certs
RUN uv sync --frozen --no-dev
COPY --from=web /web/build ./web/build
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "vemai.central:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
