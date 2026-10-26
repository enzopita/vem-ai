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
| `parts/atualiza_previsao.php` | `idPonto=<id>` | Tabela `table.table_results` (linha, prefixo do veículo, primeiro nome do motorista, previsão até 20 min) e `div#other_linhas` (linhas com previsão acima de 20 min) |
| `parts/update_bus.php` | `linha_id=<número interno>` | Posições ao vivo da linha: objetos JSON concatenados por vírgula, sem colchetes, com `prefixo`, `lat`, `lng`, `sentido` (1 ida, 2 volta) e `conteudo` (HTML do balão com motorista e horário da posição) |

Páginas `GET` da linha, por `idLinha`:

| Página | Retorno |
|---|---|
| `pg_FindLinesDt.php` | Rótulo, descrição do trajeto, itinerário (ruas da ida e da volta) e tabela horária programada (dias úteis, sábados, domingos e feriados; partida e chegada por sentido). Para uma linha de outra operadora, responde `500` com o cabeçalho em branco |
| `pg_mapaLinha.php` | Traçado (`latlngIda`, `latlngVolta`), pontos com coordenada (`ExibePontosLinha`) e o número interno da linha (`var_linha`), que `update_bus.php` pede no lugar do hash |

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

- **Coletor** (um processo por operadora, mesma imagem, configurado por variável de ambiente). Serviço HTTP que faz o scraping sob demanda e devolve JSON. O único estado é o catálogo de pontos (veja abaixo), um cache em arquivo que se reconstrói sozinho, por isso pode ser replicado e reiniciado sem perda.
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

### Catálogo de pontos

O site não tem busca por proximidade, então cada coletor monta um catálogo com código, nome e coordenada de todos os pontos da operadora, para o mapa de pontos próximos. O mapa de cada linha (`GET pg_mapaLinha.php?idLinha=`, linhas listadas em `GET pg_FindLines.php`) traz nome e coordenada dos pontos, sem código. Dos nomes saem termos de busca (o logradouro, sem número nem sufixo), e a busca de pontos devolve os códigos. A coordenada de cada código vem do centro do mapa (`initmap`) aberto com `idPonto=<código>`, que vale para qualquer ponto, mesmo fora da linha. Pontos sem coordenada ou em (0, 0) ficam de fora. As consultas rodam três por vez, com pausa entre elas, e uma falha isolada só perde aquele item.

O catálogo fica em `data/catalog-<host>.json`, um arquivo por operadora (`CATALOG_PATH` muda o caminho), e é reconstruído a cada 24 h em segundo plano. Ao subir, o coletor serve o arquivo existente, mesmo vencido, até a nova montagem terminar; sem arquivo, a lista fica vazia até a primeira montagem. Uma montagem que falha ou volta vazia não substitui o arquivo e é tentada de novo em 1 h. O coletor expõe `GET /stops/catalog`, e a central, `GET /api/stops/catalog`, que une os catálogos pelo id do ponto (mantendo o primeiro nome), em ordem de id, com `unavailable` como nas outras rotas.

### Detalhe da linha e veículos ao vivo

O coletor expõe `GET /lines/{idLinha}` (itinerário, traçado, pontos e horários, juntando a página de detalhe e o mapa) e `GET /lines/{idLinha}/vehicles` (posições ao vivo). Os dois devolvem 404 quando a operadora não conhece a linha. O coletor guarda em memória o número interno de cada linha já vista, então cada leitura de veículos custa um único `POST`.

A central expõe `GET /api/lines/{idLinha}` e `GET /api/lines/{idLinha}/vehicles`, com `?operator=` opcional. Com a operadora, só aquele coletor é consultado. Sem ela, todos são consultados e vale o primeiro que conhece a linha, na ordem de `COLLECTORS`. Se nenhum conhece e algum falhou, a resposta é 502, porque a linha pode ser justamente do coletor que falhou; se todos responderam e nenhum conhece, 404. O detalhe vem com `operator` preenchido e fica 6 h em cache na memória da central, já que itinerário e horários quase nunca mudam. As posições dos veículos nunca passam por cache. Sem `?operator=`, a rota de veículos usa a operadora do detalhe em cache, quando houver.

### Falha parcial

Se um coletor falha, a central responde 200 com o que os outros devolveram e lista as operadoras que falharam em `unavailable`. O front-end mostra um aviso discreto. Se todos falham, a resposta é 503. `GET /api/status` informa `{name, online}` de cada coletor.

O monitor segue a mesma regra, com um cuidado: quando o quadro de um ponto é parcial, os veículos do coletor ausente somem dele, o que geraria falsos alertas de "sumiu". Por isso um quadro parcial só dispara alertas de "chegando" (comparado com nada) e não é guardado como snapshot anterior. Só quadros completos viram o anterior do próximo ciclo.

## Regras de notificação

Uma inscrição tem ponto, linha (`idLinha`), horário aproximado e antecedência em minutos. Ela fica ativa de 30 min antes a 30 min depois do horário, no fuso `America/Sao_Paulo`.

A cada ciclo, para cada ponto com inscrição ativa, a central compara o snapshot anterior com o atual (o quadro da região, já unido):

- **Chegando**: veículo da linha com previsão menor ou igual à antecedência.
- **Sumiu**: veículo da linha que estava no snapshot anterior com previsão acima de 3 min e não aparece no atual. Um veículo com 3 min ou menos que some provavelmente passou pelo ponto, por isso não conta.

Cada par (inscrição, veículo, tipo, dia) gera no máximo uma notificação. A tabela de notificações tem chave única e o envio só acontece se a inserção ocorreu, o que torna o ciclo idempotente.
