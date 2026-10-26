<script lang="ts">
	import { onMount } from 'svelte';
	import type { Direction, LineDetail, ScheduleDay } from '#lib/api.ts';
	import { dayOf, nextIndex as findNext } from '#lib/schedule.ts';

	interface Props {
		line: LineDetail;
	}

	let { line }: Props = $props();

	const DAYS: { key: ScheduleDay; label: string }[] = [
		{ key: 'uteis', label: 'Dias úteis' },
		{ key: 'sabados', label: 'Sábados' },
		{ key: 'domingos', label: 'Domingos e feriados' }
	];

	let now = $state(new Date());
	const today = $derived(dayOf(now));
	let day = $state<ScheduleDay>(dayOf(new Date()));
	let picked = $state<Direction>();
	const direction = $derived(picked ?? line.directions[0]?.direction ?? 'ida');

	onMount(() => {
		const timer = setInterval(() => (now = new Date()), 30_000);
		return () => clearInterval(timer);
	});

	const trips = $derived(line.schedules.find((s) => s.day === day)?.[direction] ?? []);
	const nextIndex = $derived(day === today ? findNext(trips, now) : -1);
	// Hoje, as saídas que já passaram ficam recolhidas: a próxima aparece logo de cara.
	let showPast = $state(false);
	const pastCount = $derived(day !== today ? 0 : nextIndex < 0 ? trips.length : nextIndex);
	const firstShown = $derived(showPast ? 0 : pastCount);

	const seg =
		'grid min-h-11 cursor-pointer place-items-center rounded-lg px-2 text-center text-[0.9375rem] font-semibold text-soft has-checked:bg-surface has-checked:text-ink has-checked:shadow-card has-focus-visible:outline-3 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent has-focus-visible:outline-solid';
</script>

<div class="space-y-3">
	<fieldset class="grid grid-cols-3 gap-1 rounded-xl bg-quiet p-1">
		<legend class="sr-only">Dia</legend>
		{#each DAYS as d (d.key)}
			<label class={seg}>
				<input type="radio" name="dia" value={d.key} bind:group={day} class="sr-only" />
				{d.label}
			</label>
		{/each}
	</fieldset>

	<fieldset class="grid gap-1 rounded-xl bg-quiet p-1 {line.directions.length > 1 ? 'grid-cols-2' : ''}">
		<legend class="sr-only">Sentido</legend>
		{#each line.directions as d (d.direction)}
			<label class={seg}>
				<input type="radio" name="sentido" value={d.direction} checked={direction === d.direction} onchange={() => (picked = d.direction)} class="sr-only" />
				<span><span class="block">{d.direction === 'ida' ? 'Ida' : 'Volta'}</span><span class="block text-sm font-normal">{d.name}</span></span>
			</label>
		{/each}
	</fieldset>

	{#if trips.length === 0}
		<p class="rounded-xl border border-rule bg-surface p-4 text-soft">Sem saídas neste dia e sentido.</p>
	{:else}
		{#if nextIndex >= 0}
			<p class="px-1 text-[0.9375rem]">Próxima saída: <span class="font-bold tabular-nums">{trips[nextIndex].departure}</span></p>
		{:else if day === today}
			<p class="px-1 text-[0.9375rem] text-soft">Acabaram as saídas de hoje.</p>
		{/if}
		{#if pastCount > 0}
			<button type="button" onclick={() => (showPast = !showPast)} class="min-h-11 w-full rounded-lg border border-rule bg-surface px-3 text-[0.9375rem] font-semibold text-accent hover:bg-quiet">
				{showPast ? 'Esconder' : 'Mostrar'} {pastCount} {pastCount === 1 ? 'saída que já passou' : 'saídas que já passaram'}
			</button>
		{/if}
		<ol class="grid grid-cols-4 gap-1.5" aria-label="Saídas, com a hora de chegada ao final da linha">
			{#each trips.slice(firstShown) as t, j (t.departure + (j + firstShown))}
				{@const i = j + firstShown}
				{@const past = nextIndex < 0 ? day === today : i < nextIndex}
				<li
					title="Chegada às {t.arrival}"
					class="rounded-lg border bg-surface py-1 text-center tabular-nums {i === nextIndex ? 'border-accent ring-2 ring-accent' : 'border-rule'} {past ? 'opacity-50' : ''}"
				>
					<span class="block font-semibold">{t.departure}{#if i === nextIndex}<span class="sr-only"> (próxima)</span>{/if}</span>
					<span class="block text-[0.8125rem] text-soft"><span class="sr-only">chegada </span>{t.arrival}</span>
				</li>
			{/each}
		</ol>
	{/if}
</div>
