---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: ["frontend/src/routes/+page.svelte","frontend/src/routes/ponto/[stopId]/+page.svelte","frontend/src/routes/alertas/+page.svelte"]
---

# App Vem Aí (início, ponto, alertas)

Modo: Operate. Passageiro na calçada, uma mão, sol forte: ver se dá tempo e deixar o aviso pronto. Tema claro é a base; o escuro segue o sistema.

Escopo: visual e estrutura das três rotas, navegação e componentes. Não muda: API, atualização de 15 s, texto de operadora fora do ar, voz informal, nome. Não pode parecer site oficial, brinquedo nem painel técnico.

Decisão: ônibus que estava "chegando" e some do quadro fica riscado por uma leitura com "passou ou saiu do rastreamento", depois sai.

Histórico: a direção sorteada "Azulejo de Santos" (seed:0062686ccd61d06c) foi construída e recusada pelo usuário ("muito azul, muito a mesma coisa"; quer algo mais enterprise). O usuário tomou a saída padrão da categoria, com formas de Santos no fundo.

## Direction contract

THESIS: o app de transporte padrão da categoria, executado com o acabamento de Moovit/Citymapper, Google Maps e Linear/Stripe; Santos aparece só como forma geométrica de fundo, nunca como fantasia nos dados.

OWN-WORLD: neutros cinza com texto quase preto e contraste alto; destaque azul-mar só em ação primária, link e seleção; verde = chegando, âmbar = aviso de dado velho/parcial, vermelho = falha que bloqueia. Placa do número da linha verde se municipal, azul se intermunicipal, cinza se desconhecida. As ondas do calçadão ficam só no cabeçalho, a 4% de opacidade, deslizando devagar. Cantos médios, bordas finas, sombras discretas.

STORY: a pessoa abre e vê o ponto de sempre com os próximos tempos; no ponto, lê o tempo da linha de relance, toca na linha e o alerta fica pronto numa folha; o push a traz de volta ao ponto.

FIRST VIEWPORT: (ponto, 390 px) cabeçalho branco com a marca e as ondas do calçadão quase invisíveis por trás; cartão do ponto com voltar, código, nome e hora da leitura; lista em painel único, uma linha por linha de ônibus: placa do número (verde ou azul) à esquerda, legenda dos tipos acima, tempo na rampa fixa, sino à direita; a que chega ganha fundo verde-claro. Ação primária: tocar na linha abre a folha de alerta. Navegação inferior Início / Alertas.

FORM: saída padrão (canon) escolhida pelo usuário após recusar a direção sorteada; referências Moovit/Citymapper, Google Maps/Material, Linear/Stripe. seed:0062686ccd61d06c

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
