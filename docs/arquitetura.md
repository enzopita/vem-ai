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
- **Central**. Único dono do estado: inscrições, último snapshot por ponto, notificações já enviadas. Expõe só a API, consulta todos os coletores da região de uma vez e une as respostas, e roda o monitor a cada 30 s.
- **Front-end**. Nó próprio, em `frontend/`. Um servidor Caddy serve o SPA compilado, devolve `index.html` para qualquer rota que não seja arquivo (roteamento no navegador) e encaminha `/api/*` para a central. O PWA e a API ficam na mesma origem, o que mantém o service worker e o push funcionando sem CORS.
- **PWA**. SPA em SvelteKit (Svelte 5, TypeScript, Tailwind) com `adapter-static`. Inclui `manifest.webmanifest` e um service worker que guarda o app em cache para o modo offline e recebe o push. Em desenvolvimento o Vite faz o papel do Caddy.

A comunicação entre nós é HTTP/JSON síncrono.

### Uma região por implantação

As operadoras de uma mesma região se complementam. Na Baixada Santista a Piracicabana atende linhas municipais e a BR Mobilidade as intermunicipais, e os ids de ponto são compartilhados entre os dois sites (o ponto 9306 é o mesmo nos dois). Por isso o usuário nunca escolhe operadora: a central faz um scatter-gather e devolve a visão da região.

- `GET /api/stops?q=` consulta todos os coletores em paralelo e une os pontos pelo id, mantendo o primeiro nome, em ordem alfabética.
- `GET /api/stops/{stop_id}/board` une as previsões de todos os coletores, ordenadas por tempo. As linhas "em mais de 20 min" são a união sem repetição, sem as linhas que já têm previsão.
- Os ids de linha (`idLinha`) são hashes por site e não colidem, então a união não precisa de prefixo.
- Cada pedido tem tempo limite de 10 s por coletor.

Outra região seria outra implantação, com a sua central e os seus coletores (variável `COLLECTORS`). Não existe seletor nem cadastro de regiões.

### Falha parcial

Se um coletor falha, a central responde 200 com o que os outros devolveram e lista as operadoras que falharam em `unavailable`. O front-end mostra um aviso discreto. Se todos falham, a resposta é 503. `GET /api/status` informa `{name, online}` de cada coletor.

O monitor segue a mesma regra, com um cuidado: quando o quadro de um ponto é parcial, os veículos do coletor ausente somem dele, o que geraria falsos alertas de "sumiu". Por isso um quadro parcial só dispara alertas de "chegando" (comparado com nada) e não é guardado como snapshot anterior. Só quadros completos viram o anterior do próximo ciclo.

## Regras de notificação

Uma inscrição tem ponto, linha (`idLinha`), horário aproximado e antecedência em minutos. Ela fica ativa de 30 min antes a 30 min depois do horário, no fuso `America/Sao_Paulo`.

A cada ciclo, para cada ponto com inscrição ativa, a central compara o snapshot anterior com o atual (o quadro da região, já unido):

- **Chegando**: veículo da linha com previsão menor ou igual à antecedência.
- **Sumiu**: veículo da linha que estava no snapshot anterior com previsão acima de 3 min e não aparece no atual. Um veículo com 3 min ou menos que some provavelmente passou pelo ponto, por isso não conta.

Cada par (inscrição, veículo, tipo, dia) gera no máximo uma notificação. A tabela de notificações tem chave única e o envio só acontece se a inserção ocorreu, o que torna o ciclo idempotente.
