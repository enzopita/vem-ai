<script lang="ts">
	import type { Prediction } from '#lib/api.ts';
	import LineBadge from './LineBadge.svelte';

	let { prediction }: { prediction: Prediction } = $props();
	const arriving = $derived(prediction.eta_min === 0);
</script>

<div
	class="flex items-center gap-4 rounded-3xl p-4 shadow-sm {arriving
		? 'bg-emerald-50 ring-2 ring-emerald-400 dark:bg-emerald-950/40 dark:ring-emerald-500'
		: 'bg-white dark:bg-slate-900'}"
>
	<LineBadge line={prediction.line} />
	<div class="min-w-0 flex-1">
		<p class="font-bold">Linha {prediction.line.label}</p>
		<p class="text-sm text-slate-500 dark:text-slate-400">Veículo {prediction.vehicle}</p>
	</div>
	{#if arriving}
		<span class="animate-pulse-ring rounded-full bg-emerald-600 px-4 py-2 text-sm font-extrabold text-white">Chegando</span>
	{:else}
		<p class="text-right leading-none">
			<span class="text-3xl font-extrabold tabular-nums">{prediction.eta_min}</span>
			<span class="ml-0.5 text-sm font-semibold text-slate-500 dark:text-slate-400">min</span>
		</p>
	{/if}
</div>
