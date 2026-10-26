# Vem Aí

Aplicativo web (PWA) que avisa você por notificação push quando o ônibus que você costuma pegar está chegando ao ponto, ou quando o veículo some do rastreamento (provável perda de sinal de GPS).

Projeto da APS da UNIP: aplicação de sistema distribuído para dispositivo móvel.

Os dados vêm de web scraping dos sites "Quanto Tempo Falta?" da BR Mobilidade (Piracicabana e BR Mobilidade Baixada Santista).

## Como é distribuído

Três processos independentes se comunicam por HTTP/JSON: um **coletor** por operadora e uma **central** que guarda o estado e dispara os pushes. O **front-end** é um serviço à parte (servidor estático mais proxy reverso) e a central só expõe a API. O desenho completo, as regras de notificação e as decisões estão em [docs/arquitetura.md](docs/arquitetura.md).

```
navegador ──▶ front-end ──▶ central ──▶ coletor piracicabana  ──▶ site da operadora
  (PWA)      (Caddy)           └────▶ coletor brmobilidadebs ──▶ site da operadora
```

A central consulta todos os coletores da região de uma vez, então o usuário não escolhe operadora: pontos e linhas aparecem juntos. Se um coletor cai, a central responde com o que os outros devolveram, avisa quais falharam e o resto continua funcionando. Uma região por implantação.

## Estrutura do repositório

```
backend/    API em Python (FastAPI): central, coletores, testes, certificados e Dockerfile
frontend/   PWA em SvelteKit, com Dockerfile e Caddyfile próprios
docs/       arquitetura e material da disciplina
scripts/    dev.sh (ambiente local) e make_icons.py
compose.yaml
```

Os dois lados só se falam pela API HTTP em `/api`. O backend não conhece o front-end.

## Como rodar

Requer Python 3.12 ou mais novo, o [uv](https://docs.astral.sh/uv/), Node 24 e o [pnpm](https://pnpm.io/).

### Desenvolvimento

```sh
scripts/dev.sh
```

O script sobe os coletores em `8001` e `8002`, a central em `8000` e o Vite em http://localhost:5173, que encaminha `/api` para a central. Abra http://localhost:5173. Se a porta 5173 estiver ocupada, o Vite usa a próxima e imprime o endereço.

Para rodar só uma parte: `cd backend && uv sync && uv run uvicorn vemai.central:create_app --factory` ou `cd frontend && pnpm install && pnpm dev`. O banco SQLite e a chave VAPID ficam em `data/`, relativo ao diretório onde a central roda (`backend/data`).

### Com Docker Compose

```sh
docker compose up --build
```

Abra http://localhost:8080 (mude com `FRONTEND_PORT`). Sobe o front-end, a central e os dois coletores. O front-end é o [Caddy](https://caddyserver.com/) servindo `frontend/build`, devolvendo `index.html` para qualquer rota do SPA e encaminhando `/api/*` para a central, então o PWA e a API ficam na mesma origem. A central não é publicada no host. O banco e a chave VAPID ficam no volume `central-data`.

### Variáveis de ambiente

| Variável | Serviço | Padrão | Descrição |
|---|---|---|---|
| `OPERATOR_BASE_URL` | coletor | (obrigatória) | URL base do site da operadora |
| `COLLECTORS` | central | (vazia) | Lista `nome=url` separada por vírgulas |
| `MONITOR_INTERVAL_S` | central | `30` | Intervalo do monitor, em segundos |
| `DB_PATH` | central | `data/vemai.db` | Arquivo SQLite |
| `VAPID_SUBJECT` | central | `mailto:admin@example.com` | Contato enviado aos serviços de push |

A chave VAPID é gerada na primeira execução em `data/vapid_private.pem`.

### API da central

| Rota | Função |
|---|---|
| `GET /api/stops?q=` | Busca pontos em todos os coletores (mín. 3 letras). Devolve `{stops, unavailable}` |
| `GET /api/stops/{stop_id}/board` | Previsões unidas de todas as operadoras, mais `unavailable` |
| `GET /api/status` | `[{name, online}]` por coletor |
| `GET /api/vapid-public-key` | Chave pública VAPID |
| `POST /api/subscriptions` | Cria um alerta (ponto, linha, horário, antecedência) |
| `GET /api/subscriptions?endpoint=` | Lista os alertas deste aparelho |
| `DELETE /api/subscriptions/{id}?endpoint=` | Exclui um alerta |
| `POST /api/subscriptions/{id}/test?endpoint=` | Envia uma notificação de teste |

`unavailable` lista as operadoras cujo coletor falhou naquele pedido. Se todos falham, a resposta é 503.

### Testes

```sh
cd backend && uv run pytest
cd frontend && pnpm check
```

## Front-end

SvelteKit (Svelte 5, TypeScript, Tailwind CSS v4) compilado como SPA estático com `adapter-static`, em `frontend/`.

| Caminho | Função |
|---|---|
| `src/routes/+page.svelte` | Busca de pontos na região |
| `src/routes/ponto/[stopId]` | Painel do ponto, atualizado a cada 15 s, com o formulário de alerta |
| `src/routes/alertas` | Alertas deste aparelho, com testar e excluir |
| `src/lib/api.ts` | Cliente tipado da API da central |
| `src/lib/push.ts` | Permissão, inscrição Web Push e detecção de suporte |
| `src/lib/components/` | Componentes pequenos (cartões, busca, formulário, toast) |
| `src/service-worker/` | Cache do app para uso offline, recebimento do push e clique na notificação |
| `static/` | Manifesto e ícones (`scripts/make_icons.py` gera os PNG) |

Comandos: `pnpm check` (tipos), `pnpm build` e `pnpm preview`.

## Notificações no celular

O Web Push só funciona em HTTPS ou em `localhost`. Para testar no celular, exponha o front-end (Compose, porta 8080) com um túnel HTTPS:

```sh
cloudflared tunnel --url http://localhost:8080
```

Abra o endereço `https://...trycloudflare.com` no celular. No iPhone é preciso tocar em Compartilhar, escolher "Adicionar à Tela de Início" e abrir o app por lá.

## Particularidades do scraping

- Sem um `User-Agent` de navegador os sites respondem `403`.
- Os servidores não enviam o certificado intermediário (GlobalSign Atlas R3 AlphaSSL CA 2026 Q2). O arquivo `backend/certs/globalsign-alphassl-2026q2.pem` é somado ao bundle do `certifi`, então a verificação TLS continua ligada.
- O rótulo da linha varia entre a tabela (`04`) e a lista de previsões acima de 20 min (`CIRCULAR 004`). O identificador estável é o hash `idLinha`.
- `CHEGANDO!` significa 3 minutos ou menos e vira previsão `0`.
- A busca de pontos exige pelo menos 3 letras.
