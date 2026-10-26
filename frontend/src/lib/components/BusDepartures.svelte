<script lang="ts">
	import { onMount } from 'svelte';
	import type { LineDetail } from '#lib/api.ts';
	import { DIRECTION_COLORS } from '#lib/map.ts';
	import { dayOf, nextIndex } from '#lib/schedule.ts';

	interface Props {
		line: LineDetail;
	}

	let { line }: Props = $props();

	const SHOWN = 4;

	let now = $state(new Date());
	onMount(() => {
		const timer = setInterval(() => (now = new Date()), 30_000);
		return () => clearInterval(timer);
	});

	const rows = $derived.by(() => {
		const day = dayOf(now);
		const schedule = line.schedules.find((s) => s.day === day);
		return line.directions.map((d) => {
			const trips = schedule?.[d.direction] ?? [];
			const from = nextIndex(trips, now);
			return { ...d, next: from < 0 ? [] : trips.slice(from, from + SHOWN) };
		});
	});
</script>

<section aria-labelledby="saidas-title" class="space-y-2">
	<h3 id="saidas-title" class="font-bold">Próximas saídas de hoje</h3>
	{#each rows as row (row.direction)}
		<div class="space-y-1">
			<p class="flex items-center gap-1.5 text-sm">
				<span class="h-1.5 w-4 shrink-0 rounded-full" style:background={DIRECTION_COLORS[row.direction]} aria-hidden="true"></span>
				<span class="min-w-0 truncate"><span class="font-semibold">{row.direction === 'ida' ? 'Ida' : 'Volta'}:</span> <span class="text-soft">{row.name}</span></span>
			</p>
			{#if row.next.length === 0}
				<p class="rounded-lg border border-rule bg-quiet px-3 py-2 text-[0.9375rem] text-soft">Sem mais saídas hoje</p>
			{:else}
				<ol class="grid grid-cols-4 gap-1.5">
					{#each row.next as trip, i (trip.departure + i)}
						<li class="rounded-lg border py-1.5 text-center font-semibold tabular-nums {i === 0 ? 'border-accent bg-accent text-on-accent' : 'border-rule bg-surface'}">
							{trip.departure}{#if i === 0}<span class="sr-only"> (próxima)</span>{/if}
						</li>
					{/each}
				</ol>
			{/if}
		</div>
	{/each}
</section>
