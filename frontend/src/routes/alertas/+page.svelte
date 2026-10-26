<script lang="ts">
	import { lineLabel } from '#lib/names.ts';
	import { onMount } from 'svelte';
	import { flip } from 'svelte/animate';
	import { fade, fly } from 'svelte/transition';
	import { api, messageOf, type Subscription } from '#lib/api.ts';
	import AlertCard from '#lib/components/AlertCard.svelte';
	import PushHelp from '#lib/components/PushHelp.svelte';
	import { currentSubscription, pushSupport } from '#lib/push.ts';
	import { notify } from '#lib/toast.svelte.ts';

	let support = $state(pushSupport());
	let alerts = $state<Subscription[]>([]);
	let loading = $state(true);
	let error = $state('');
	let busyId = $state<number | null>(null);

	async function load() {
		loading = true;
		error = '';
		try {
			// Bloqueado ainda pode ter inscrição antiga: os alertas aparecem, com o aviso de que não vão chegar.
			const sub = support === 'supported' || support === 'denied' ? await currentSubscription() : null;
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
			notify('info', `Alerta da linha ${lineLabel(alert.line_label)} excluído.`, { label: 'Desfazer', run: () => void restore(alert) });
		});

	// Desfazer recria o alerta com os mesmos dados; o id muda, o resto continua igual.
	async function restore({ id: _id, ...alert }: Subscription) {
		try {
			await api.createSubscription(alert);
		} catch (err) {
			notify('error', messageOf(err));
		}
		await load();
	}

	function recheck() {
		support = pushSupport();
		void load();
	}

	onMount(load);
</script>

<svelte:head><title>Meus alertas · Vem Aí</title></svelte:head>

<div class="space-y-4 pb-4">
	<section class="space-y-1 px-1">
		<h1 class="text-[1.75rem] leading-tight font-bold tracking-tight">Meus alertas</h1>
		<p class="text-soft">Os avisos ativos neste aparelho. Cada um vigia a linha de 30 min antes a 30 min depois do horário.</p>
	</section>

	{#if support !== 'supported'}
		<PushHelp {support} onrecheck={recheck} />
	{/if}

	{#if loading}
		<ul class="space-y-3" aria-label="Carregando alertas">
			{#each [0, 1] as i (i)}
				<li class="h-40 animate-shimmer rounded-xl border border-rule bg-surface"></li>
			{/each}
		</ul>
	{:else if error}
		<div class="rounded-lg bg-danger-bg p-4 text-danger" role="alert">
			<p class="font-bold">{error}</p>
			<button type="button" onclick={load} class="mt-3 rounded-lg bg-danger px-5 font-bold text-danger-bg hover:brightness-110">Tentar de novo</button>
		</div>
	{:else if alerts.length === 0 && support === 'supported'}
		<div class="overflow-hidden rounded-xl border border-rule bg-surface shadow-card" in:fade>
			<div class="p-5">
				<p class="text-lg font-bold">Nenhum alerta neste aparelho ainda</p>
				<p class="mt-1 text-soft">Abra o seu ponto e toque na linha que você pega. O aviso chega sozinho no horário de sempre.</p>
				<a href="/" class="mt-4 inline-flex items-center rounded-lg bg-accent px-5 font-semibold text-on-accent hover:brightness-110">Escolher o ponto</a>
			</div>
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
