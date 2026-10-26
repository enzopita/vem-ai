<script lang="ts">
	import { flip } from 'svelte/animate';
	import { fade } from 'svelte/transition';
	import { page } from '$app/state';
	import { api, messageOf, type Line, type RegionBoard } from '#lib/api.ts';
	import { clock, groupByLine, vanishedArrivals, type Arrival } from '#lib/board.ts';
	import AlertSheet from '#lib/components/AlertSheet.svelte';
	import BusSheet, { type Tracked } from '#lib/components/BusSheet.svelte';
	import LineRow from '#lib/components/LineRow.svelte';
	import LineTile from '#lib/components/LineTile.svelte';
	import UnavailableNotice from '#lib/components/UnavailableNotice.svelte';
	import { kindSuffix, lineKind } from '#lib/operators.ts';
	import { stopLabel, lineLabel } from '#lib/names.ts';
	import { recentStops, rememberStop } from '#lib/recent.ts';

	const REFRESH_MS = 15_000;

	const stopId = $derived(page.params.stopId ?? '');
	// Um link sem ?nome (de fora do app) ainda recupera o nome se o ponto já foi aberto neste aparelho.
	const knownName = $derived(page.url.searchParams.get('nome') ?? recentStops().find((s) => s.id === stopId)?.name);
	const stopName = $derived(knownName ?? `Ponto ${stopId}`);

	let board = $state<RegionBoard | null>(null);
	let vanished = $state<Line[]>([]);
	let error = $state('');
	let refreshing = $state(false);
	let tick = $state(0);
	let updatedAt = $state<Date | null>(null);
	let announcement = $state('');
	let alertLine = $state<Line | null>(null);
	let busPick = $state<{ line: Line; arrival?: Arrival } | null>(null);

	const groups = $derived(board ? groupByLine(board) : []);
	// A legenda só mostra os tipos que aparecem neste ponto.
	const kinds = $derived(
		new Set([...(board?.predictions.map((p) => p.line) ?? []), ...(board?.other_lines ?? [])].map((l) => lineKind(l.operator)).filter(Boolean))
	);
	const stale = $derived(!!error && !!board);
	// A folha do ônibus segue a previsão que atualiza a cada 15 s; o ônibus que sumiu do quadro fica sem tempo.
	const busLive = $derived.by((): Tracked | undefined => {
		const picked = busPick?.arrival;
		if (!busPick || !picked) return undefined;
		const found = groups.find((g) => g.line.id === busPick!.line.id)?.arrivals.find((a) => a.vehicle === picked.vehicle);
		return { ...picked, eta: found?.eta ?? null };
	});

	let current: AbortController | undefined;

	async function refresh() {
		current?.abort();
		const ctrl = (current = new AbortController());
		refreshing = true;
		try {
			const next = await api.board(stopId, ctrl.signal);
			vanished = vanishedArrivals(board, next);
			announce(board, next);
			board = next;
			error = '';
			updatedAt = new Date();
		} catch (err) {
			if (ctrl.signal.aborted) return;
			error = messageOf(err);
		} finally {
			if (!ctrl.signal.aborted) {
				refreshing = false;
				tick++;
			}
		}
	}

	// Leitores de tela ouvem só as linhas que passaram a "chegando", não a lista inteira a cada 15 s.
	function announce(prev: RegionBoard | null, next: RegionBoard) {
		const before = new Set(prev?.predictions.filter((p) => p.eta_min === 0).map((p) => p.line.id));
		const arriving = new Map(next.predictions.filter((p) => p.eta_min === 0 && !before.has(p.line.id)).map((p) => [p.line.id, p.line.label]));
		if (prev && arriving.size > 0) announcement = `Chegando: linha ${[...arriving.values()].join(', linha ')}.`;
	}

	$effect(() => {
		board = null;
		vanished = [];
		error = '';
		updatedAt = null;
		alertLine = null;
		busPick = null;
		void refresh();
		const timer = setInterval(refresh, REFRESH_MS);
		const onVisible = () => document.visibilityState === 'visible' && void refresh();
		document.addEventListener('visibilitychange', onVisible);
		return () => {
			clearInterval(timer);
			document.removeEventListener('visibilitychange', onVisible);
			current?.abort();
		};
	});

	$effect(() => {
		if (knownName) rememberStop({ id: stopId, name: knownName });
	});
</script>

<svelte:head><title>{stopLabel(stopName)} · Vem Aí</title></svelte:head>

<div class="space-y-3 pb-2">
	<section class="relative overflow-hidden rounded-xl border border-rule bg-surface px-4 pt-1 pb-1.5 shadow-card" aria-labelledby="stop-title">
		<div class="flex items-center justify-between gap-3 text-[0.9375rem]">
			<a href="/" class="-ml-2 inline-flex items-center gap-1 rounded-lg px-2 font-semibold text-accent hover:bg-quiet">
				<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
				Trocar ponto
			</a>
			<span class="rounded-md bg-quiet px-2 py-0.5 text-sm font-semibold text-soft">Ponto {stopId}</span>
		</div>
		<h1 id="stop-title" class="text-lg leading-snug font-bold tracking-tight text-balance">{stopLabel(stopName)}</h1>
		<div class="mt-1 flex items-center justify-between gap-3 border-t border-rule pt-1 text-sm">
			<p class="flex items-center gap-1.5 text-soft">
				{#if refreshing}
					<svg viewBox="0 0 24 24" class="size-4 shrink-0 animate-spin text-accent" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9" /></svg>
				{/if}
				<span>{#if stale && updatedAt}Leitura das {clock(updatedAt)}{:else if updatedAt}Atualizado às {clock(updatedAt)}{:else}Lendo as previsões…{/if}</span>
			</p>
			<button type="button" onclick={refresh} disabled={refreshing} class="rounded-lg px-3 font-semibold text-accent hover:bg-quiet disabled:opacity-60">
				Atualizar
			</button>
		</div>
		<div class="absolute inset-x-0 bottom-0 h-0.5 overflow-hidden bg-quiet" aria-hidden="true">
			{#key tick}
				<div class="h-full origin-left bg-accent {refreshing ? 'w-full animate-shimmer' : 'animate-countdown'}"></div>
			{/key}
		</div>
	</section>

	<p class="sr-only" aria-live="polite">{announcement}</p>

	{#if error}
		<div class="rounded-xl bg-warn-bg p-4 text-warn" role="alert">
			<p class="font-bold">{error}</p>
			{#if board}<p class="mt-1 text-[0.9375rem]">As previsões tracejadas são da última leitura. Tentamos de novo a cada 15 segundos.</p>{/if}
		</div>
	{/if}

	{#if board}<UnavailableNotice unavailable={board.unavailable} />{/if}

	{#if !board && !error}
		<ul class="space-y-2.5" aria-label="Carregando previsões">
			{#each [0, 1, 2] as i (i)}
				<li class="h-20 animate-shimmer rounded-xl border border-rule bg-surface"></li>
			{/each}
		</ul>
	{:else if board}
		<section aria-labelledby="next-title" class="space-y-1.5">
			<div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-1">
				<h2 id="next-title" class="text-sm font-semibold text-soft">Até 20 min{groups.length > 0 ? ` · ${groups.length}` : ''}<span class="sr-only"> · toque na linha para ver onde está o ônibus, ou no sino para ser avisado</span></h2>
				{#if kinds.size > 0}
					<ul class="flex gap-3 text-xs text-soft" aria-label="Tipos de linha">
						{#if kinds.has('municipal')}<li class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm bg-municipal" aria-hidden="true"></span>Municipal</li>{/if}
						{#if kinds.has('intermunicipal')}<li class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm bg-intermunicipal" aria-hidden="true"></span>Intermunicipal</li>{/if}
					</ul>
				{/if}
			</div>
			{#if groups.length === 0 && vanished.length === 0}
				<div class="overflow-hidden rounded-xl border border-rule bg-surface shadow-card {stale ? 'antigo' : ''}" in:fade>
					<div class="p-5">
						<p class="text-lg font-bold">Nenhum ônibus a menos de 20 min</p>
						<p class="mt-1 text-[0.9375rem] text-soft">A tela atualiza sozinha a cada 15 segundos.</p>
					</div>
				</div>
			{:else}
				<ul class="painel rolagem max-h-[21rem] {stale ? 'antigo' : ''}">
					{#each vanished as line (`sumiu-${line.id}`)}
						<li in:fade={{ duration: 200 }} out:fade={{ duration: 150 }}>
							<div class="flex min-h-11 items-center gap-3 bg-quiet px-3 py-1.5 text-soft">
								<span class="flex w-12 shrink-0"><LineTile label={line.label} operator={line.operator} size="sm" /></span>
								<span class="sr-only">Linha {lineLabel(line.label)}{kindSuffix(line.operator)}:</span>
								<p class="w-20 shrink-0 text-base font-bold line-through decoration-2">Chegando</p>
								<p class="min-w-0 flex-1 text-sm leading-tight">Passou ou saiu do rastreamento.</p>
							</div>
						</li>
					{/each}
					{#each groups as group (group.line.id)}
						<li animate:flip={{ duration: 250 }} in:fade={{ duration: 200 }} out:fade={{ duration: 150 }}>
							<LineRow {group} {stale} onbus={(g) => (busPick = { line: g.line, arrival: g.arrivals[0] })} onalert={(line) => (alertLine = line)} />
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		{#if board.other_lines.length > 0}
			<section aria-labelledby="later-title" class="space-y-1.5">
				<h2 id="later-title" class="px-1 text-sm font-semibold text-soft">Também passam aqui, a mais de 20 min · {board.other_lines.length}</h2>
				<ul class="painel rolagem max-h-[8.25rem] {stale ? 'antigo' : ''}">
					{#each board.other_lines as line (line.id)}
						<li in:fade>
							<div class="flex items-stretch bg-surface">
								<button type="button" onclick={() => (busPick = { line })} class="flex min-h-11 min-w-0 flex-1 items-center gap-3 py-1.5 pr-1 pl-3 text-left hover:bg-quiet focus-visible:-outline-offset-4">
									<!-- Coluna de largura fixa: o itinerário começa no mesmo ponto em todas as linhas. -->
									<span class="flex w-12 shrink-0"><LineTile label={line.label} operator={line.operator} size="sm" /></span>
									<span class="min-w-0 flex-1">
										<span class="sr-only">Linha {lineLabel(line.label)}{kindSuffix(line.operator)}{line.description ? ':' : ''}</span>
										<span class="line-clamp-2 text-sm leading-snug text-soft">{line.description || 'Sem previsão nos próximos 20 min'}</span>
									</span>
								</button>
								<button type="button" onclick={() => (alertLine = line)} aria-label="Avisar da linha {lineLabel(line.label)}" class="grid w-11 shrink-0 place-items-center text-soft hover:bg-quiet focus-visible:-outline-offset-4">
									<svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0" /></svg>
								</button>
							</div>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	{/if}
</div>

<BusSheet
	{stopId}
	{stopName}
	line={busPick?.line ?? null}
	bus={busLive}
	onclose={() => (busPick = null)}
	onalert={(line) => {
		busPick = null;
		alertLine = line;
	}}
/>
<AlertSheet {stopId} {stopName} line={alertLine} onclose={() => (alertLine = null)} />
