<script lang="ts">
	import { ApiError, api, messageOf, type LatLng, type Line, type LineDetail } from '#lib/api.ts';
	import type { Arrival } from '#lib/board.ts';
	import { loadCatalog } from '#lib/catalog.ts';
	import { lineLabel, personName, stopLabel } from '#lib/names.ts';
	import { kindSuffix } from '#lib/operators.ts';
	import BusDepartures from './BusDepartures.svelte';
	import BusMap from './BusMap.svelte';
	import LineTile from './LineTile.svelte';

	/** Ônibus que a pessoa tocou. `eta` é null quando ele saiu da previsão do ponto desde o toque. */
	export type Tracked = Omit<Arrival, 'eta'> & { eta: number | null };

	interface Props {
		stopId: string;
		stopName: string;
		/** A linha tocada no quadro; null fecha a folha. */
		line: Line | null;
		/** Ausente quando a pessoa tocou numa linha sem ônibus previsto. */
		bus?: Tracked;
		onclose: () => void;
		onalert: (line: Line) => void;
	}

	let { stopId, stopName, line, bus, onclose, onalert }: Props = $props();

	type Remote =
		| { kind: 'loading' }
		| { kind: 'ready'; detail: LineDetail; stop: LatLng | null }
		| { kind: 'failed'; reason: string };

	let dialog: HTMLDialogElement;
	let title = $state<HTMLHeadingElement>();
	let remote = $state<Remote>({ kind: 'loading' });

	const lineId = $derived(line?.id);
	const operator = $derived(line?.operator ?? '');

	$effect(() => {
		if (line) {
			if (!dialog.open) {
				dialog.showModal();
				title?.focus();
			}
		} else if (dialog.open) {
			dialog.close();
		}
	});

	$effect(() => {
		const id = lineId;
		const op = operator;
		if (!id) return;
		const ctrl = new AbortController();
		remote = { kind: 'loading' };
		// Sem coordenada do ponto o mapa ainda serve: o catálogo é um extra, a linha é o que importa.
		const stop = loadCatalog()
			.then((c) => c.stops.find((s) => s.id === stopId) ?? null)
			.catch(() => null);
		Promise.all([api.line(id, op, ctrl.signal), stop]).then(
			([detail, here]) => {
				if (!ctrl.signal.aborted) remote = { kind: 'ready', detail, stop: here };
			},
			(err) => {
				if (ctrl.signal.aborted) return;
				remote = { kind: 'failed', reason: err instanceof ApiError && err.status === 404 ? 'A operadora não informa mapa e horários desta linha.' : messageOf(err) };
			}
		);
		return () => ctrl.abort();
	});

	const icon = 'size-4 shrink-0 text-soft';
</script>

<dialog
	bind:this={dialog}
	class="folha"
	aria-labelledby="bus-title"
	{onclose}
	onclick={(e) => e.target === dialog && dialog.close()}
>
	{#if line}
		<div class="space-y-4 p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
			<header class="space-y-3">
				<div class="flex items-center gap-3">
					<LineTile label={line.label} operator={line.operator} />
					<div class="min-w-0 flex-1">
						<h2 id="bus-title" bind:this={title} tabindex="-1" class="text-xl leading-tight font-bold outline-none">Linha {lineLabel(line.label)}<span class="sr-only">{kindSuffix(line.operator)}</span></h2>
						<p class="truncate text-[0.9375rem] text-soft">{(remote.kind === 'ready' ? remote.detail.description : line.description) || stopLabel(stopName)}</p>
					</div>
					<button type="button" onclick={() => dialog.close()} aria-label="Fechar" class="grid min-w-11 place-items-center rounded-lg text-soft hover:bg-quiet">
						<svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
					</button>
				</div>
				{#if bus}
					<div class="flex items-center justify-between gap-3">
						<div class="min-w-0 space-y-0.5 text-[0.9375rem] leading-tight">
							{#if bus.vehicle}
								<p class="flex items-center gap-1.5">
									<svg viewBox="0 0 24 24" class={icon} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 6v6" /><path d="M15 6v6" /><path d="M2 12h19.6" /><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3" /><circle cx="7" cy="18" r="2" /><path d="M9 18h5" /><circle cx="16" cy="18" r="2" /></svg>
									<span class="truncate"><span class="sr-only">Ônibus </span>{bus.vehicle}</span>
								</p>
							{/if}
							{#if bus.driver}
								<p class="flex items-center gap-1.5 text-soft">
									<svg viewBox="0 0 24 24" class={icon} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
									<span class="truncate"><span class="sr-only">Motorista </span>{personName(bus.driver)}</span>
								</p>
							{/if}
						</div>
						<p class="shrink-0 text-right leading-none whitespace-nowrap" aria-live="polite">
							{#if bus.eta === null}
								<span class="text-sm font-semibold text-soft">Saiu da previsão</span>
							{:else if bus.eta === 0}
								<span class="text-2xl font-bold tracking-tight text-ok">Chegando</span>
							{:else}
								<span class="text-3xl font-bold tracking-tight">{bus.eta}</span> <span class="text-sm font-semibold text-soft">min</span>
							{/if}
							<span class="mt-1 block text-xs text-soft">até este ponto</span>
						</p>
					</div>
				{/if}
			</header>

			{#if remote.kind === 'loading'}
				<div class="h-56 animate-shimmer rounded-xl border border-rule bg-surface" aria-hidden="true"></div>
				<p class="sr-only" role="status">Carregando o mapa e os horários…</p>
			{:else if remote.kind === 'failed'}
				<p class="rounded-xl border border-rule bg-quiet px-4 py-3 text-[0.9375rem] text-soft" role="status">{remote.reason}</p>
			{:else}
				<BusMap line={remote.detail} {operator} prefix={bus?.vehicle || undefined} stop={remote.stop} />
				<BusDepartures line={remote.detail} />
			{/if}

			<div class="space-y-2">
				<button type="button" onclick={() => onalert(line)} class="w-full rounded-lg bg-accent px-6 py-3 text-lg font-bold text-on-accent transition hover:brightness-110 active:translate-y-px">
					Avisar quando chegar
				</button>
				{#if remote.kind === 'ready'}
					<a href="/linha/{encodeURIComponent(line.id)}?op={encodeURIComponent(operator)}&rotulo={encodeURIComponent(line.label)}" class="flex min-h-11 items-center justify-center rounded-lg border border-rule bg-quiet px-4 font-semibold">
						Mapa e horários completos
					</a>
				{/if}
			</div>
		</div>
	{/if}
</dialog>
