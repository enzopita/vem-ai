<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type CollectorStatus, type RegionBoard } from '#lib/api.ts';
	import { clock, groupByLine } from '#lib/board.ts';
	import NearbyStops from '#lib/components/NearbyStops.svelte';
	import LineTile from '#lib/components/LineTile.svelte';
	import StopSearch from '#lib/components/StopSearch.svelte';
	import { stopLabel, lineLabel } from '#lib/names.ts';
	import { kindSuffix, operatorLabel } from '#lib/operators.ts';
	import { recentStops, stopHref } from '#lib/recent.ts';

	const recents = recentStops();
	const mine = recents[0];
	const others = recents.slice(1);

	let status = $state<CollectorStatus[]>([]);
	let board = $state<RegionBoard | null>(null);
	let boardFailed = $state(false);
	let readAt = $state<Date | null>(null);
	const offline = $derived(status.filter((c) => !c.online).map((c) => operatorLabel(c.name)));
	const nearest = $derived(board ? groupByLine(board).slice(0, 4) : []);

	onMount(() => {
		api.status().then(
			(s) => (status = s),
			() => {} // a linha de status é só um extra; a busca mostra o erro quando importar
		);
		if (mine) {
			api.board(mine.id).then(
				(b) => {
					board = b;
					readAt = new Date();
				},
				() => (boardFailed = true)
			);
		}
	});
</script>

<svelte:head><title>Vem Aí: seu ponto</title></svelte:head>

<div class="space-y-4 pb-2">
	<h1 class="sr-only">Vem Aí: seu ponto</h1>
	<StopSearch label="Buscar linha ou ponto" />

	{#if mine}
		<section aria-labelledby="mine-title" class="space-y-2">
			<a href={stopHref(mine)} class="block rounded-xl border border-rule bg-surface px-4 pt-3 pb-2 shadow-card hover:border-soft">
				<h2 id="mine-title" class="text-lg leading-snug font-bold tracking-tight text-balance"><span class="sr-only">Seu ponto: </span>{stopLabel(mine.name)}</h2>
				<div class="mt-2 border-t border-rule pt-3">
					{#if nearest.length > 0}
						<ul class="grid grid-cols-2 gap-x-3 gap-y-1.5">
							{#each nearest as group (group.line.id)}
								<li class="flex min-w-0 items-center gap-2">
									<LineTile label={group.line.label} operator={group.line.operator} size="sm" />
									<span class="sr-only">Linha {lineLabel(group.line.label)}{kindSuffix(group.line.operator)}:</span>
									<span class="truncate text-base font-bold tracking-tight {group.arrivals[0].eta === 0 ? 'text-ok' : ''}">{group.arrivals[0].eta === 0 ? 'Chegando' : `${group.arrivals[0].eta} min`}</span>
								</li>
							{/each}
						</ul>
					{:else if board}
						<p class="text-soft">Nenhum ônibus a menos de 20 min agora.</p>
					{:else if boardFailed}
						<p class="text-soft">Sem previsão agora. Abra o ponto para tentar de novo.</p>
					{:else}
						<p class="text-soft">Lendo as previsões…</p>
					{/if}
					<div class="mt-3 flex items-center justify-between gap-3 text-[0.9375rem]">
						<p class="text-soft">{#if readAt}Atualizado às {clock(readAt)}{/if}</p>
						<p class="flex shrink-0 items-center gap-1 font-semibold text-accent">
							Abrir o ponto
							<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
						</p>
					</div>
				</div>
			</a>
			{#if others.length > 0}
				<ul class="space-y-2" aria-label="Outros pontos recentes">
					{#each others as stop (stop.id)}
						<li>
							<a href={stopHref(stop)} class="flex items-center gap-3 rounded-xl border border-rule bg-surface px-4 py-1.5 font-semibold hover:border-soft">
								<span class="min-w-0 flex-1 truncate">{stopLabel(stop.name)}</span>
								<svg viewBox="0 0 24 24" class="size-5 shrink-0 text-soft" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{:else}
		<p class="px-1 text-soft">Busque o ponto, toque na sua linha e a gente manda uma notificação quando o ônibus estiver chegando.</p>
	{/if}

	{#if offline.length > 0}
		<p class="px-1 text-[0.9375rem] text-soft">{offline.join(' e ')} fora do ar no momento.</p>
	{/if}

	<div class="border-t border-rule pt-3">
		<NearbyStops />
	</div>
</div>
