# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Passageiro de ônibus da Baixada Santista que pega a mesma linha, no mesmo ponto, em horário parecido todo dia. Usa o celular na rua: indo para o ponto ou já esperando nele, muitas vezes com uma mão só, sob sol forte e com pressa. O trabalho dele é saber se dá tempo, quando sair e se o ônibus vem mesmo, sem perder a viagem.

## Product Purpose

O Vem Aí avisa por notificação push quando o ônibus que a pessoa costuma pegar está chegando ao ponto, ou quando o veículo some do rastreamento (provável perda de sinal de GPS). A pessoa cadastra ponto, linha, horário aproximado e antecedência uma vez, e depois não precisa abrir nada: o aviso chega na hora certa. Sucesso é o passageiro chegar ao ponto a tempo e não ficar esperando um ônibus que não vem.

Também é o trabalho da APS da UNIP (sistema distribuído para dispositivo móvel), apresentado academicamente. A arquitetura precisa continuar simples de explicar.

## Positioning

O site oficial "Quanto Tempo Falta?" da BR Mobilidade só responde quando consultado e não foi feito para o celular. O Vem Aí:

- **Avisa sozinho**: o push chega no horário habitual, sem a pessoa ficar abrindo e atualizando o site.
- **Detecta sumiço**: alerta quando o veículo que estava a caminho some do rastreamento, coisa que o site não faz.
- **É feito para o celular**: PWA instalável, legível e rápido na mão.

## Operating Context

- Consulta rápida na rua: buscar um ponto, ver as previsões, decidir se sai agora.
- Configuração rara: o alerta é criado uma vez e roda sozinho; a maior parte do valor chega pela notificação, fora do app.
- Dados vindos de scraping dos sites "Quanto Tempo Falta?" da Piracicabana e da BR Mobilidade Baixada Santista. Uma região por implantação; o usuário nunca escolhe operadora, pontos e linhas das duas aparecem juntos.
- Previsões só existem até 20 min com veículo identificado; acima disso o site dá apenas a lista de linhas. `CHEGANDO!` significa 3 min ou menos.
- No iPhone o push só funciona com o app adicionado à Tela de Início e aberto por lá.

## Capabilities and Constraints

- Busca de pontos na região (mín. 3 letras), painel do ponto atualizado a cada 15 s, criação de alerta (ponto, linha, horário, antecedência), lista de alertas do aparelho com testar e excluir.
- Alerta ativo de 30 min antes a 30 min depois do horário, fuso `America/Sao_Paulo`. Cada par (alerta, veículo, tipo, dia) gera no máximo uma notificação.
- Falha parcial: se o coletor de uma operadora cai, o app mostra o que as outras devolveram e um aviso discreto de quem está fora do ar.
- Web Push exige HTTPS (ou `localhost`). Funciona offline para abrir o app; previsões exigem rede.
- Sem conta nem login: os alertas pertencem ao aparelho (endpoint de push).
- Arquitetura distribuída (coletores, central, front-end) mantida simples por ser trabalho acadêmico. Detalhes em `docs/arquitetura.md`.

## Brand Commitments

- Nome fixo: **Vem Aí**.
- Voz informal e próxima, em português do Brasil, como uma conversa ("seu ônibus está chegando").
- Visual no padrão enterprise da categoria, no nível de acabamento de Moovit/Citymapper, Google Maps/Material e Linear/Stripe: neutros com contraste alto, um destaque azul-mar usado pouco, cor de estado só onde há significado.
- Santos entra como forma geométrica de fundo, nunca atrás de dados: as ondas do calçadão da orla, bem sutis e em movimento lento, só no cabeçalho.
- Linhas têm cor pelo tipo, como nos ônibus da Baixada: verde é municipal, azul é intermunicipal.

## Evidence on Hand

- Fixtures reais de HTML dos sites das operadoras em `backend/tests/fixtures/`.
- Orientações da APS em `docs/aps-orientacoes-2020-2.pdf`.
- Não há usuários, depoimentos, métricas de uso nem parceria com a BR Mobilidade. Não inventar nenhum deles.

## Product Principles

1. **O aviso é o produto.** A notificação certa na hora certa vale mais que qualquer tela; o app existe para configurar e conferir.
2. **Lido em um relance, na rua.** Toda tela precisa ser entendida em segundos, com uma mão, sob sol.
3. **Honesto sobre a incerteza.** Mostrar quando o dado é parcial, quando o GPS sumiu e quando uma operadora está fora, em vez de fingir precisão.
4. **Zero escolhas desnecessárias.** O passageiro pensa em ponto e linha, nunca em operadora ou em infraestrutura.
5. **Simples de explicar.** Produto e arquitetura precisam caber numa apresentação acadêmica.

## Accessibility & Inclusion

Uso na rua, sob sol: contraste alto, leitura rápida, alvos de toque grandes (mínimo 44 px, já aplicado em `frontend/src/app.css`) e operação com uma mão. Respeitar `prefers-reduced-motion` (já aplicado).
