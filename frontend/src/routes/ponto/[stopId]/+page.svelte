<script lang="ts">
	import { flip } from 'svelte/animate';
	import { fade } from 'svelte/transition';
	import { page } from '$app/state';
	import { api, messageOf, type Line, type RegionBoard } from '#lib/api.ts';
	import AlertForm from '#lib/components/AlertForm.svelte';
	import LineBadge from '#lib/components/LineBadge.svelte';
	import PredictionRow from '#lib/components/PredictionRow.svelte';
	import UnavailableNotice from '#lib/components/UnavailableNotice.svelte';

	const REFRESH_MS = 15_000;

	const stopId = $derived(page.params.stopId ?? '');
	const stopName = $derived(page.url.searchParams.get('nome') ?? `Ponto ${stopId}`);

	let board = $state<RegionBoard | null>(null);
	let error = $state('');
	let refreshing = $state(false);
	let tick = $state(0);
	let updatedAt = $state<Date | null>(null);

	const predictions = $derived([...(board?.predictions ?? [])].sort((a, b) => a.eta_min - b.eta_min));
	// Linhas vistas neste ponto desde que a tela abriu, em ordem de número: se dependessem só da leitura atual,
	// a opção escolhida no alerta mudaria de lugar ou sumiria quando o ônibus sai do quadro.
	let lines = $state<Line[]>([]);

	function remember(seen: RegionBoard) {
		const byId = new Map(lines.map((line) => [line.id, line]));
		for (const line of [...seen.predictions.map((p) => p.line), ...seen.other_lines]) byId.set(line.id, line);
		lines = [...byId.values()].sort((a, b) => a.label.localeCompare(b.label, 'pt-BR', { numeric: true }));
	}

	let current: AbortController | undefined;

	async function refresh() {
		current?.abort();
		const ctrl = (current = new AbortController());
		refreshing = true;
		try {
			board = await api.board(stopId, ctrl.signal);
			remember(board);
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

	$effect(() => {
		board = null;
		lines = [];
		error = '';
		updatedAt = null;
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
</script>

<svelte:head><title>{stopName} · Vem Aí</title></svelte:head>

<div class="space-y-5 pb-4">
	<section class="overflow-hidden rounded-[2rem] bg-white shadow-xl shadow-indigo-900/10 dark:bg-slate-900 dark:shadow-black/30" aria-labelledby="stop-title">
		<div class="p-5">
			<a href="/" class="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-violet-600 dark:text-violet-300">
				<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
				Trocar ponto
			</a>
			<p class="text-xs font-bold tracking-wide text-slate-500 uppercase dark:text-slate-400">Ponto {stopId}</p>
			<h1 id="stop-title" class="text-xl leading-snug font-extrabold text-balance">{stopName}</h1>
			<div class="mt-3 flex items-center justify-between gap-3 text-sm text-slate-500 dark:text-slate-400">
				<span>{updatedAt ? `Atualizado às ${updatedAt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : 'Carregando…'}</span>
				<button
					type="button"
					onclick={refresh}
					disabled={refreshing}
					class="rounded-xl px-3 font-semibold text-violet-600 hover:bg-violet-50 disabled:opacity-50 dark:text-violet-300 dark:hover:bg-violet-950/50"
				>
					{refreshing ? 'Atualizando…' : 'Atualizar'}
				</button>
			</div>
		</div>
		<div class="h-1.5 bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label="Próxima atualização" aria-hidden="true">
			{#key tick}
				<div class="h-full origin-left bg-linear-to-r from-indigo-500 to-fuchsia-500 {refreshing ? 'w-full animate-shimmer' : 'animate-countdown'}"></div>
			{/key}
		</div>
	</section>

	{#if error}
		<div class="rounded-3xl bg-rose-50 p-4 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200" role="alert">
			<p class="font-semibold">{error}</p>
			{#if board}<p class="mt-1 text-sm opacity-80">Mostrando a última leitura. Tentaremos de novo em instantes.</p>{/if}
		</div>
	{/if}

	{#if board}<UnavailableNotice unavailable={board.unavailable} />{/if}

	{#if !board && !error}
		<div class="space-y-3" aria-label="Carregando previsões">
			{#each [0, 1, 2] as i (i)}
				<div class="h-24 animate-shimmer rounded-3xl bg-white dark:bg-slate-900"></div>
			{/each}
		</div>
	{:else if board}
		<section aria-labelledby="next-title" class="space-y-3">
			<h2 id="next-title" class="px-1 text-sm font-bold tracking-wide text-slate-600 uppercase dark:text-slate-400">Próximos ônibus</h2>
			{#if predictions.length === 0}
				<div class="rounded-3xl bg-white p-8 text-center dark:bg-slate-900" in:fade>
					<p class="text-3xl" aria-hidden="true">🚏</p>
					<p class="mt-2 font-bold">Nenhum ônibus previsto agora</p>
					<p class="text-sm text-slate-500 dark:text-slate-400">A tela atualiza sozinha a cada 15 segundos.</p>
				</div>
			{:else}
				<ul class="space-y-3">
					{#each predictions as prediction (prediction.line.id + prediction.vehicle)}
						<li animate:flip={{ duration: 250 }} in:fade={{ duration: 200 }} out:fade={{ duration: 150 }}>
							<PredictionRow {prediction} />
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		{#if board.other_lines.length > 0}
			<section aria-labelledby="later-title" class="rounded-3xl bg-white p-4 dark:bg-slate-900">
				<h2 id="later-title" class="mb-3 text-sm font-bold tracking-wide text-slate-600 uppercase dark:text-slate-400">Em mais de 20 min</h2>
				<ul class="flex flex-wrap gap-2">
					{#each board.other_lines as line (line.id)}
						<li in:fade><LineBadge {line} small /></li>
					{/each}
				</ul>
			</section>
		{/if}

		<AlertForm {stopId} {stopName} {lines} />
	{/if}
</div>
