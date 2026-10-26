<script lang="ts">
	import { lineLabel } from '#lib/names.ts';
	import { page } from '$app/state';
	import { api, ApiError, messageOf, type LineDetail } from '#lib/api.ts';
	import LineMap from '#lib/components/LineMap.svelte';
	import LineSchedule from '#lib/components/LineSchedule.svelte';
	import LineTile from '#lib/components/LineTile.svelte';
	import { operatorLabel } from '#lib/operators.ts';

	type Tab = 'mapa' | 'horarios';
	const TABS: { key: Tab; label: string }[] = [
		{ key: 'mapa', label: 'Mapa' },
		{ key: 'horarios', label: 'Horários' }
	];

	const lineId = $derived(page.params.lineId ?? '');
	const operator = $derived(page.url.searchParams.get('op') ?? '');
	// O rótulo vem na URL para o cabeçalho aparecer antes da resposta.
	const label = $derived(page.url.searchParams.get('rotulo') ?? '');

	let detail = $state<LineDetail | null>(null);
	let error = $state('');
	let attempt = $state(0);
	let tab = $state<Tab>('mapa');

	const title = $derived(detail?.label ?? label);

	$effect(() => {
		const id = lineId;
		const op = operator;
		void attempt;
		const ctrl = new AbortController();
		detail = null;
		error = '';
		api.line(id, op, ctrl.signal).then(
			(d) => (detail = d),
			(err) => {
				if (ctrl.signal.aborted) return;
				// 404 é a operadora dizendo que não conhece a linha; o resto é falha de rede ou do site.
				error =
					err instanceof ApiError && err.status === 404
						? 'Não encontramos o mapa e os horários desta linha no site da operadora.'
						: `Não conseguimos carregar a linha agora. ${messageOf(err)}`;
			}
		);
		return () => ctrl.abort();
	});

	function back(event: MouseEvent) {
		if (history.length > 1) {
			event.preventDefault();
			history.back();
		}
	}

	function onKey(event: KeyboardEvent) {
		const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
		if (!step && event.key !== 'Home' && event.key !== 'End') return;
		event.preventDefault();
		const at = TABS.findIndex((t) => t.key === tab);
		const next = event.key === 'Home' ? 0 : event.key === 'End' ? TABS.length - 1 : (at + step + TABS.length) % TABS.length;
		tab = TABS[next].key;
		document.getElementById(`tab-${tab}`)?.focus();
	}
</script>

<svelte:head><title>Linha {lineLabel(title)} · Vem Aí</title></svelte:head>

<div class="space-y-3 pb-2">
	<header class="rounded-xl border border-rule bg-surface px-4 pt-1 pb-3 shadow-card">
		<a href="/" onclick={back} class="-ml-2 inline-flex items-center gap-1 rounded-lg px-2 text-[0.9375rem] font-semibold text-accent hover:bg-quiet">
			<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
			Voltar
		</a>
		<div class="mt-1 flex items-center gap-3">
			<LineTile label={title} {operator} />
			<div class="min-w-0 flex-1">
				<h1 class="text-lg leading-tight font-bold tracking-tight">Linha {lineLabel(title)}</h1>
				{#if operator}<p class="text-sm text-soft">{operatorLabel(operator)}</p>{/if}
			</div>
		</div>
		{#if detail?.description}
			<p class="mt-2 line-clamp-2 text-sm text-soft">{detail.description}</p>
		{/if}
	</header>

	<div role="tablist" aria-label="Mapa e horários" class="grid grid-cols-2 gap-1 rounded-xl bg-quiet p-1">
		{#each TABS as t (t.key)}
			<button
				type="button"
				role="tab"
				id="tab-{t.key}"
				aria-selected={tab === t.key}
				aria-controls="panel-{t.key}"
				tabindex={tab === t.key ? 0 : -1}
				onclick={() => (tab = t.key)}
				onkeydown={onKey}
				class="min-h-11 rounded-lg font-semibold {tab === t.key ? 'bg-surface text-ink shadow-card' : 'text-soft'}"
			>
				{t.label}
			</button>
		{/each}
	</div>

	<div role="tabpanel" id="panel-{tab}" aria-labelledby="tab-{tab}">
		{#if error}
			<div class="rounded-xl bg-warn-bg p-4 text-warn" role="alert">
				<p class="font-semibold">{error}</p>
				<button type="button" onclick={() => attempt++} class="mt-3 min-h-11 rounded-lg bg-surface px-4 font-semibold text-ink">Tentar de novo</button>
			</div>
		{:else if !detail}
			<div class="h-[55dvh] min-h-[280px] animate-shimmer rounded-xl border border-rule bg-surface" aria-hidden="true"></div>
			<p class="sr-only" role="status">Carregando a linha…</p>
		{:else if tab === 'mapa'}
			<LineMap line={detail} {operator} />
		{:else}
			<LineSchedule line={detail} />
		{/if}
	</div>
</div>
