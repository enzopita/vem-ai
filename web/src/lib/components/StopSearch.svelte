<script lang="ts">
	import { fly } from 'svelte/transition';
	import { api, messageOf, type Stop } from '#lib/api.ts';

	let { operator }: { operator: string } = $props();

	const MIN_CHARS = 3;
	let query = $state('');
	let stops = $state<Stop[]>([]);
	let loading = $state(false);
	let error = $state('');

	const term = $derived(query.trim());

	$effect(() => {
		const q = term;
		const op = operator;
		stops = [];
		error = '';
		if (q.length < MIN_CHARS) {
			loading = false;
			return;
		}
		loading = true;
		const ctrl = new AbortController();
		const timer = setTimeout(async () => {
			try {
				stops = await api.searchStops(op, q, ctrl.signal);
				loading = false;
			} catch (err) {
				if (ctrl.signal.aborted) return;
				error = messageOf(err);
				loading = false;
			}
		}, 350);
		return () => {
			clearTimeout(timer);
			ctrl.abort();
		};
	});

	const href = (stop: Stop) => `/ponto/${encodeURIComponent(operator)}/${encodeURIComponent(stop.id)}?nome=${encodeURIComponent(stop.name)}`;
</script>

<div class="rounded-3xl bg-white p-4 shadow-sm dark:bg-slate-900">
	<label for="stop-query" class="mb-2 block text-sm font-bold">Buscar ponto</label>
	<div class="relative">
		<svg viewBox="0 0 24 24" class="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
		<input
			id="stop-query"
			type="search"
			bind:value={query}
			autocomplete="off"
			placeholder="Nome da rua ou código do ponto"
			class="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pr-4 pl-11 placeholder:text-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-700 dark:bg-slate-800 dark:focus:bg-slate-800"
		/>
	</div>

	<div class="mt-3" aria-live="polite">
		{#if error}
			<p class="rounded-2xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">{error}</p>
		{:else if term.length < MIN_CHARS}
			<p class="px-1 text-sm text-slate-500 dark:text-slate-400">Digite pelo menos {MIN_CHARS} letras para buscar.</p>
		{:else if loading}
			<ul class="space-y-2" aria-label="Buscando">
				{#each [0, 1, 2] as i (i)}
					<li class="h-14 animate-shimmer rounded-2xl bg-slate-100 dark:bg-slate-800"></li>
				{/each}
			</ul>
		{:else if stops.length === 0}
			<p class="px-1 text-sm text-slate-500 dark:text-slate-400">Nenhum ponto encontrado para "{term}".</p>
		{:else}
			<ul class="space-y-2">
				{#each stops as stop, i (stop.id)}
					<li in:fly={{ y: 10, duration: 200, delay: Math.min(i, 8) * 25 }}>
						<a
							href={href(stop)}
							class="flex items-center gap-3 rounded-2xl bg-slate-50 p-3 transition-colors hover:bg-violet-50 dark:bg-slate-800 dark:hover:bg-violet-950/50"
						>
							<span class="rounded-lg bg-violet-100 px-2 py-1 font-mono text-sm font-bold text-violet-700 dark:bg-violet-900/60 dark:text-violet-200">{stop.id}</span>
							<span class="min-w-0 flex-1 text-sm font-medium">{stop.name}</span>
							<svg viewBox="0 0 24 24" class="size-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
