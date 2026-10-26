# syntax=docker/dockerfile:1.7
FROM node:24-slim AS build
ENV PNPM_HOME=/pnpm PATH="/pnpm:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app
# O pnpm vem da versão fixada em packageManager; a camada só muda quando o package.json muda.
COPY package.json pnpm-lock.yaml .npmrc ./
RUN corepack enable && corepack install
# A store do pnpm fica num cache do BuildKit: mudar uma dependência baixa só ela.
RUN --mount=type=cache,id=vemai-pnpm-store,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM caddy:2.10-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/build /srv
EXPOSE 80
