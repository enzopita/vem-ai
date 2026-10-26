<script lang="ts">
	import { onMount } from 'svelte';
	import { flip } from 'svelte/animate';
	import { fade, fly } from 'svelte/transition';
	import { api, messageOf, type Subscription } from '#lib/api.ts';
	import AlertCard from '#lib/components/AlertCard.svelte';
	import { currentSubscription, pushSupport } from '#lib/push.ts';
	import { notify } from '#lib/toast.svelte.ts';

	const support = pushSupport();
	let alerts = $state<Subscription[]>([]);
	let loading = $state(true);
	let error = $state('');
	let busyId = $state<number | null>(null);

	async function load() {
		loading = true;
		error = '';
		try {
			const sub = support === 'supported' ? await currentSubscription() : null;
			alerts = sub ? await api.listSubscriptions(sub.endpoint) : [];
		} catch (err) {
			error = messageOf(err);
		} finally {
			loading = false;
		}
	}

	async function act(alert: Subscription, run: () => Promise<void>) {
		busyId = alert.id;
		try {
			await run();
		} catch (err) {
			notify('error', messageOf(err));
			await load();
		} finally {
			busyId = null;
		}
	}

	const test = (alert: Subscription) =>
		act(alert, async () => {
			await api.testSubscription(alert);
			notify('ok', 'Notificação de teste enviada.');
		});

	const remove = (alert: Subscription) =>
		act(alert, async () => {
			await api.deleteSubscription(alert);
			alerts = alerts.filter((a) => a.id !== alert.id);
			notify('info', 'Alerta excluído.');
		});

	onMount(load);
</script>

<svelte:head><title>Meus alertas · Vem Aí</title></svelte:head>

<div class="space-y-4 pb-4">
	<section class="rounded-[2rem] bg-white p-5 shadow-xl shadow-indigo-900/10 dark:bg-slate-900 dark:shadow-black/30">
		<h1 class="text-xl font-extrabold">Meus alertas</h1>
		<p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Os avisos ativos neste aparelho.</p>
	</section>

	{#if support === 'needs-home-screen'}
		<p class="rounded-3xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
			No iPhone, toque em Compartilhar e escolha "Adicionar à Tela de Início". Abra o app por lá para receber avisos.
		</p>
	{:else if support === 'unsupported'}
		<p class="rounded-3xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
			Este navegador não suporta notificações push, então não há alertas neste aparelho.
		</p>
	{/if}

	{#if loading}
		<div class="space-y-3" aria-label="Carregando alertas">
			{#each [0, 1] as i (i)}
				<div class="h-36 animate-shimmer rounded-3xl bg-white dark:bg-slate-900"></div>
			{/each}
		</div>
	{:else if error}
		<div class="rounded-3xl bg-rose-50 p-4 dark:bg-rose-950/40" role="alert">
			<p class="font-semibold text-rose-800 dark:text-rose-200">{error}</p>
			<button type="button" onclick={load} class="mt-3 rounded-xl bg-violet-600 px-5 font-semibold text-white hover:bg-violet-700">Tentar de novo</button>
		</div>
	{:else if alerts.length === 0}
		<div class="rounded-3xl bg-white p-10 text-center dark:bg-slate-900" in:fade>
			<p class="text-4xl" aria-hidden="true">🔔</p>
			<p class="mt-3 text-lg font-bold">Nenhum alerta neste aparelho</p>
			<p class="mx-auto mt-1 max-w-xs text-sm text-slate-500 dark:text-slate-400">Abra um ponto e ative um alerta para ser avisado quando o ônibus estiver chegando.</p>
			<a href="/" class="mt-5 inline-flex items-center rounded-2xl bg-linear-to-r from-indigo-600 to-fuchsia-600 px-6 font-bold text-white shadow-lg shadow-violet-500/30">Escolher um ponto</a>
		</div>
	{:else}
		<ul class="space-y-3">
			{#each alerts as alert (alert.id)}
				<li animate:flip={{ duration: 250 }} in:fly={{ y: 12, duration: 220 }} out:fly={{ x: -40, duration: 200 }}>
					<AlertCard {alert} busy={busyId === alert.id} ontest={test} ondelete={remove} />
				</li>
			{/each}
		</ul>
	{/if}
</div>
