<script lang="ts">
	import { onMount } from 'svelte';
	import { api, messageOf, type Operator } from '#lib/api.ts';
	import { loadLastOperator, saveLastOperator } from '#lib/lastOperator.ts';
	import OperatorCard from '#lib/components/OperatorCard.svelte';
	import StopSearch from '#lib/components/StopSearch.svelte';

	let operators = $state<Operator[]>([]);
	let loading = $state(true);
	let error = $state('');
	let selected = $state<string | null>(null);

	async function load() {
		loading = true;
		error = '';
		try {
			operators = await api.operators();
			const last = loadLastOperator();
			if (operators.some((o) => o.name === last && o.online)) selected = last;
		} catch (err) {
			error = messageOf(err);
		} finally {
			loading = false;
		}
	}

	function select(name: string) {
		selected = name;
		saveLastOperator(name);
	}

	onMount(load);
</script>

<svelte:head><title>Vem Aí: escolha seu ponto</title></svelte:head>

<div class="space-y-6 pb-4">
	<section aria-labelledby="op-title" class="rounded-[2rem] bg-white p-4 shadow-xl shadow-indigo-900/10 dark:bg-slate-900 dark:shadow-black/30">
		<h2 id="op-title" class="mb-3 px-1 text-sm font-bold tracking-wide text-slate-600 uppercase dark:text-slate-400">1. Escolha a operadora</h2>
		{#if loading}
			<div class="grid gap-3 sm:grid-cols-2" aria-label="Carregando operadoras">
				{#each [0, 1] as i (i)}
					<div class="h-20 animate-shimmer rounded-3xl bg-slate-100 dark:bg-slate-800"></div>
				{/each}
			</div>
		{:else if error}
			<div class="rounded-2xl bg-rose-50 p-4 dark:bg-rose-950/40" role="alert">
				<p class="font-semibold text-rose-700 dark:text-rose-300">{error}</p>
				<button type="button" onclick={load} class="mt-3 rounded-xl bg-violet-600 px-5 font-semibold text-white hover:bg-violet-700">Tentar de novo</button>
			</div>
		{:else if operators.length === 0}
			<p class="p-2 text-slate-600 dark:text-slate-300">Nenhuma operadora configurada.</p>
		{:else}
			<div class="grid gap-3 sm:grid-cols-2">
				{#each operators as operator (operator.name)}
					<OperatorCard {operator} selected={selected === operator.name} onselect={select} />
				{/each}
			</div>
		{/if}
	</section>

	{#if selected}
		<section aria-labelledby="stop-title">
			<h2 id="stop-title" class="mb-3 px-1 text-sm font-bold tracking-wide text-slate-600 uppercase dark:text-slate-400">2. Encontre o ponto</h2>
			{#key selected}
				<StopSearch operator={selected} />
			{/key}
		</section>
	{/if}
</div>
