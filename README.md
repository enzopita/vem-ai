# Vem Aí

Aplicativo web (PWA) que avisa você por notificação push quando o ônibus que você costuma pegar está chegando ao ponto, ou quando o veículo some do rastreamento (provável perda de sinal de GPS).

Projeto da APS da UNIP: aplicação de sistema distribuído para dispositivo móvel.

Os dados vêm de web scraping dos sites "Quanto Tempo Falta?" da BR Mobilidade (Piracicabana e BR Mobilidade Baixada Santista).

## Como é distribuído

Três processos independentes se comunicam por HTTP/JSON: um **coletor** por operadora e uma **central** que guarda o estado, serve a PWA e dispara os pushes. O desenho completo, as regras de notificação e as decisões estão em [docs/arquitetura.md](docs/arquitetura.md).

```
navegador (PWA) ──▶ central ──▶ coletor piracicabana  ──▶ site da operadora
                        └────▶ coletor brmobilidadebs ──▶ site da operadora
```

Se um coletor cai, a central marca a operadora como offline e as demais continuam funcionando.

## Como rodar

Requer Python 3.12 ou mais novo, o [uv](https://docs.astral.sh/uv/), Node 24 e o [pnpm](https://pnpm.io/).

### Desenvolvimento

```sh
uv sync
scripts/dev.sh          # coletores em 8001 e 8002, central em 8000
cd web && pnpm install
pnpm dev                # front-end em http://localhost:5173, com proxy de /api para a central
```

Abra http://localhost:5173. O Vite recarrega a página a cada alteração em `web/src`.

### Produção local

```sh
cd web && pnpm install && pnpm build
cd .. && scripts/dev.sh
```

O `pnpm build` gera o SPA em `web/build`, e a central o serve em http://localhost:8000. Qualquer caminho que não seja `/api/*` nem um arquivo existente devolve o `index.html`, então links diretos como `/alertas` funcionam ao recarregar. Sem `web/build`, a central expõe só a API.

### Com Docker Compose

```sh
docker compose up --build
```

Sobe a central (`8000`) e os dois coletores com a mesma imagem. O build em duas etapas compila o front-end com Node e copia `web/build` para a imagem Python. O banco SQLite e a chave VAPID ficam no volume `central-data`.

### Variáveis de ambiente

| Variável | Serviço | Padrão | Descrição |
|---|---|---|---|
| `OPERATOR_BASE_URL` | coletor | (obrigatória) | URL base do site da operadora |
| `COLLECTORS` | central | (vazia) | Lista `nome=url` separada por vírgulas |
| `MONITOR_INTERVAL_S` | central | `30` | Intervalo do monitor, em segundos |
| `DB_PATH` | central | `data/vemai.db` | Arquivo SQLite |
| `VAPID_SUBJECT` | central | `mailto:admin@example.com` | Contato enviado aos serviços de push |

A chave VAPID é gerada na primeira execução em `data/vapid_private.pem`.

### Testes

```sh
uv run pytest
```

## Front-end

SvelteKit (Svelte 5, TypeScript, Tailwind CSS v4) compilado como SPA estático com `adapter-static`, em `web/`.

| Caminho | Função |
|---|---|
| `src/routes/+page.svelte` | Escolha da operadora e busca de pontos |
| `src/routes/ponto/[operator]/[stopId]` | Painel do ponto, atualizado a cada 15 s, com o formulário de alerta |
| `src/routes/alertas` | Alertas deste aparelho, com testar e excluir |
| `src/lib/api.ts` | Cliente tipado da API da central |
| `src/lib/push.ts` | Permissão, inscrição Web Push e detecção de suporte |
| `src/lib/components/` | Componentes pequenos (cartões, busca, formulário, toast) |
| `src/service-worker/` | Cache do app para uso offline, recebimento do push e clique na notificação |
| `static/` | Manifesto e ícones (`scripts/make_icons.py` gera os PNG) |

Comandos: `pnpm check` (tipos), `pnpm build` e `pnpm preview`.

## Notificações no celular

O Web Push só funciona em HTTPS ou em `localhost`. Para testar no celular, exponha a central com um túnel HTTPS:

```sh
cloudflared tunnel --url http://localhost:8000
```

Abra o endereço `https://...trycloudflare.com` no celular. No iPhone é preciso tocar em Compartilhar, escolher "Adicionar à Tela de Início" e abrir o app por lá.

## Particularidades do scraping

- Sem um `User-Agent` de navegador os sites respondem `403`.
- Os servidores não enviam o certificado intermediário (GlobalSign Atlas R3 AlphaSSL CA 2026 Q2). O arquivo `certs/globalsign-alphassl-2026q2.pem` é somado ao bundle do `certifi`, então a verificação TLS continua ligada.
- O rótulo da linha varia entre a tabela (`04`) e a lista de previsões acima de 20 min (`CIRCULAR 004`). O identificador estável é o hash `idLinha`.
- `CHEGANDO!` significa 3 minutos ou menos e vira previsão `0`.
- A busca de pontos exige pelo menos 3 letras.
