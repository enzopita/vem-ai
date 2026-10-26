<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type CollectorStatus } from '#lib/api.ts';
	import { operatorLabel } from '#lib/operators.ts';
	import StopSearch from '#lib/components/StopSearch.svelte';

	let status = $state<CollectorStatus[]>([]);
	const offline = $derived(status.filter((c) => !c.online).map((c) => operatorLabel(c.name)));

	onMount(async () => {
		try {
			status = await api.status();
		} catch {
			// a linha de status é só um extra; a busca mostra o erro quando importar
		}
	});
</script>

<svelte:head><title>Vem Aí: escolha seu ponto</title></svelte:head>

<div class="space-y-3 pb-4">
	<StopSearch />
	{#if offline.length > 0}
		<p class="px-2 text-center text-xs text-slate-500 dark:text-slate-400">{offline.join(' e ')} fora do ar no momento.</p>
	{/if}
</div>
