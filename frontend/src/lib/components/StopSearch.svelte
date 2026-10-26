<script lang="ts">
	import { fade } from 'svelte/transition';
	import { page } from '$app/state';
	import { api, messageOf, type Line, type Stop } from '#lib/api.ts';
	import { lineLabel, stopLabel } from '#lib/names.ts';
	import { stopHref } from '#lib/recent.ts';
	import LineTile from './LineTile.svelte';
	import UnavailableNotice from './UnavailableNotice.svelte';

	let { label }: { label: string } = $props();

	const MIN_CHARS = 3;
	let query = $state(page.url.searchParams.get('q') ?? '');

	type Results =
		| { kind: 'idle' }
		| { kind: 'loading' }
		| { kind: 'done'; lines: Line[]; stops: Stop[]; unavailable: string[]; error: string };
	let results = $state<Results>({ kind: 'idle' });

	const term = $derived(query.trim());
	// Número de linha tem 2 ou 3 dígitos ("04", "154"); rua e itinerário pedem pelo menos 3 letras.
	const wantsLines = (q: string) => /\d/.test(q) || q.length >= MIN_CHARS;
	const wantsStops = (q: string) => q.length >= MIN_CHARS;

	// Leitores de tela ouvem o resumo, não os links um por um.
	const summary = $derived.by(() => {
		if (results.kind !== 'done') return '';
		const { lines, stops } = results;
		if (lines.length + stops.length === 0) return `Nada encontrado para ${term}.`;
		const parts = [];
		if (lines.length) parts.push(`${lines.length} ${lines.length === 1 ? 'linha' : 'linhas'}`);
		if (stops.length) parts.push(`${stops.length} ${stops.length === 1 ? 'ponto' : 'pontos'}`);
		return `${parts.join(' e ')} encontrados.`;
	});

	const lineHref = (line: Line) => `/linha/${line.id}?op=${encodeURIComponent(line.operator ?? '')}&rotulo=${encodeURIComponent(line.label)}`;

	$effect(() => {
		const q = term;
		if (!wantsLines(q) && !wantsStops(q)) {
			results = { kind: 'idle' };
			return;
		}
		results = { kind: 'loading' };
		const ctrl = new AbortController();
		const timer = setTimeout(async () => {
			// Uma busca falhando não esconde o que a outra achou.
			const [lines, stops] = await Promise.allSettled([
				wantsLines(q) ? api.searchLines(q, ctrl.signal) : Promise.resolve({ lines: [], unavailable: [] }),
				wantsStops(q) ? api.searchStops(q, ctrl.signal) : Promise.resolve({ stops: [], unavailable: [] })
			]);
			if (ctrl.signal.aborted) return;
			const failed = [lines, stops].find((r) => r.status === 'rejected');
			results = {
				kind: 'done',
				lines: lines.status === 'fulfilled' ? lines.value.lines : [],
				stops: stops.status === 'fulfilled' ? stops.value.stops : [],
				unavailable: [
					...new Set([
						...(lines.status === 'fulfilled' ? lines.value.unavailable : []),
						...(stops.status === 'fulfilled' ? stops.value.unavailable : [])
					])
				],
				error: failed ? messageOf(failed.reason) : ''
			};
		}, 350);
		return () => {
			clearTimeout(timer);
			ctrl.abort();
		};
	});
</script>

<section class="space-y-2">
	<label for="stop-query" class="block px-1 text-sm font-semibold text-soft">{label}</label>
	<div class="relative">
		<svg viewBox="0 0 24 24" class="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-soft" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
		<input
			id="stop-query"
			type="search"
			bind:value={query}
			autocomplete="off"
			enterkeyhint="search"
			placeholder="Linha, rua ou código do ponto"
			aria-describedby="stop-hint"
			class="min-h-12 w-full rounded-xl border border-rule bg-surface pr-4 pl-11 text-base shadow-card placeholder:text-soft focus:border-accent"
		/>
	</div>

	<p class="sr-only" aria-live="polite">{summary}</p>

	{#if results.kind === 'idle'}
		<p id="stop-hint" class="px-1 text-[0.8125rem] text-soft">Número da linha, {MIN_CHARS} letras da rua ou o código da placa.</p>
	{:else if results.kind === 'loading'}
		<ul class="space-y-2" aria-label="Buscando">
			{#each [0, 1, 2] as i (i)}
				<li class="h-14 animate-shimmer rounded-xl border border-rule bg-surface"></li>
			{/each}
		</ul>
	{:else}
		{#if results.unavailable.length > 0}<UnavailableNotice unavailable={results.unavailable} />{/if}
		{#if results.error}<p class="rounded-lg bg-danger-bg p-3 text-[0.9375rem] text-danger">{results.error}</p>{/if}
		{#if results.lines.length + results.stops.length === 0 && !results.error}
			<div class="px-1 text-[0.9375rem] text-soft">
				<p>Nada encontrado para "{term}".</p>
				<p>Tente o número da linha, só o nome da rua, sem número, ou o código escrito na placa.</p>
			</div>
		{/if}
		{#if results.lines.length > 0}
			<section aria-labelledby="found-lines" class="space-y-1.5">
				<h2 id="found-lines" class="px-1 text-sm font-semibold text-soft">Linhas · {results.lines.length}</h2>
				<ul class="painel rolagem max-h-[8.25rem]">
					{#each results.lines as line (line.operator + line.id)}
						<li in:fade={{ duration: 150 }}>
							<a href={lineHref(line)} class="flex min-h-11 items-center gap-3 bg-surface px-3 py-1.5 hover:bg-quiet focus-visible:-outline-offset-4">
								<span class="flex w-12 shrink-0"><LineTile label={line.label} operator={line.operator} size="sm" /></span>
								<span class="min-w-0 flex-1">
									<span class="sr-only">Linha {lineLabel(line.label)}: </span>
									<span class="line-clamp-2 text-sm leading-snug text-soft">{line.description || 'Mapa e horários da linha'}</span>
								</span>
								<svg viewBox="0 0 24 24" class="size-5 shrink-0 text-soft" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
		{#if results.stops.length > 0}
			<section aria-labelledby="found-stops" class="space-y-1.5">
				<h2 id="found-stops" class="px-1 text-sm font-semibold text-soft">Pontos · {results.stops.length}</h2>
				<ul class="painel rolagem max-h-[19rem]" aria-labelledby="found-stops">
					{#each results.stops as stop (stop.id)}
						<li in:fade={{ duration: 150 }}>
							<a href={stopHref(stop)} class="flex items-center gap-3 bg-surface px-4 py-3 hover:bg-quiet focus-visible:-outline-offset-4">
								<span class="min-w-14 rounded-md bg-quiet px-2 py-0.5 text-center text-sm font-semibold text-soft">{stop.id}</span>
								<span class="min-w-0 flex-1 font-semibold">{stopLabel(stop.name)}</span>
								<svg viewBox="0 0 24 24" class="size-5 shrink-0 text-soft" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	{/if}
</section>
