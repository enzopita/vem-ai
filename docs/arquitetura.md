# Vem Aí: arquitetura

Aplicação PWA que avisa o usuário, por Web Push, quando o ônibus que ele costuma pegar está chegando ao ponto, ou quando o veículo some do rastreamento (provável perda de sinal de GPS). Os dados vêm de web scraping dos sites "Quanto Tempo Falta?" da BR Mobilidade.

## Fontes de dados

Os dois sites rodam o mesmo sistema PHP, então um único parser atende ambos.

| Operadora | URL base |
|---|---|
| `piracicabana` | `https://quantotempofalta.piracicabana.com.br` |
| `brmobilidadebs` | `https://quantotempofalta.brmobilidadebs.com.br` |

Endpoints usados (todos `POST application/x-www-form-urlencoded`, resposta HTML em UTF-8):

| Endpoint | Parâmetro | Retorno |
|---|---|---|
| `parts/select_option.php` | `var_pesq=<texto, mín. 3 letras>` | Links `pg_QuantoTempoFalta.php?idPonto=<id>` com texto `"<id> - <endereço>"` |
| `parts/atualiza_previsao.php` | `idPonto=<id>` | Tabela `table.table_results` (linha, prefixo do veículo, previsão até 20 min) e `div#other_linhas` (linhas com previsão acima de 20 min) |

Cada linha de ônibus é identificada por `idLinha` (hash SHA-1 no `href`/`onclick` de `pg_mapaLinha.php`). O rótulo varia entre a tabela (`04`) e a lista (`CIRCULAR 004`), por isso o identificador estável é o hash.

A previsão aparece como `CHEGANDO!` (3 minutos ou menos, tratado como 0) ou `N minutos`.

Restrições observadas nos servidores:

- Sem `User-Agent` de navegador a resposta é `403`.
- O servidor não envia o certificado intermediário (GlobalSign Atlas R3 AlphaSSL CA 2026 Q2). O arquivo `backend/certs/globalsign-alphassl-2026q2.pem` é somado ao bundle do `certifi` para a verificação TLS passar sem desligá-la.

## Componentes distribuídos

```
              ┌───────────────┐    ┌────────────────────────┐
 navegador ──▶│  front-end    │───▶│  central (FastAPI)     │──▶ serviço de push do navegador
 (PWA + SW)   │  Caddy: SPA   │    │  SQLite, monitor, VAPID│    (FCM, Mozilla, Apple)
              │  + proxy /api │    └──────┬──────────┬──────┘
              └───────────────┘      HTTP │          │ HTTP
                              ┌───────────▼───┐  ┌───▼────────────┐
                              │ coletor       │  │ coletor        │
                              │ piracicabana  │  │ brmobilidadebs │
                              └──────┬────────┘  └──────┬─────────┘
                                     ▼                  ▼
                               site da operadora   site da operadora
```

- **Coletor** (um processo por operadora, mesma imagem, configurado por variável de ambiente). Serviço HTTP sem estado que faz o scraping sob demanda e devolve JSON. Pode ser replicado e reiniciado sem perda.
- **Central**. Único dono do estado: inscrições, último snapshot por ponto, notificações já enviadas. Expõe só a API, faz proxy das buscas para o coletor certo e roda o monitor a cada 30 s.
- **Front-end**. Nó próprio, em `frontend/`. Um servidor Caddy serve o SPA compilado, devolve `index.html` para qualquer rota que não seja arquivo (roteamento no navegador) e encaminha `/api/*` para a central. O PWA e a API ficam na mesma origem, o que mantém o service worker e o push funcionando sem CORS.
- **PWA**. SPA em SvelteKit (Svelte 5, TypeScript, Tailwind) com `adapter-static`. Inclui `manifest.webmanifest` e um service worker que guarda o app em cache para o modo offline e recebe o push. Em desenvolvimento o Vite faz o papel do Caddy.

A comunicação entre nós é HTTP/JSON síncrono. Se um coletor cai, a central registra o erro, marca a operadora como indisponível em `/api/operators` e tenta de novo no próximo ciclo; as outras operadoras seguem funcionando.

## Regras de notificação

Uma inscrição tem operadora, ponto, linha (`idLinha`), horário aproximado e antecedência em minutos. Ela fica ativa de 30 min antes a 30 min depois do horário, no fuso `America/Sao_Paulo`.

A cada ciclo, para cada ponto com inscrição ativa, a central compara o snapshot anterior com o atual:

- **Chegando**: veículo da linha com previsão menor ou igual à antecedência.
- **Sumiu**: veículo da linha que estava no snapshot anterior com previsão acima de 3 min e não aparece no atual. Um veículo com 3 min ou menos que some provavelmente passou pelo ponto, por isso não conta.

Cada par (inscrição, veículo, tipo, dia) gera no máximo uma notificação. A tabela de notificações tem chave única e o envio só acontece se a inserção ocorreu, o que torna o ciclo idempotente.
