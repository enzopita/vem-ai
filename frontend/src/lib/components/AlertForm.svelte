<script lang="ts">
	import { api, messageOf, type Line } from '#lib/api.ts';
	import { permissionDenied, pushSupport, subscribe } from '#lib/push.ts';
	import { notify } from '#lib/toast.svelte.ts';

	interface Props {
		stopId: string;
		stopName: string;
		lines: Line[];
	}

	let { stopId, stopName, lines }: Props = $props();

	const support = pushSupport();
	const now = new Date();
	let chosenLine = $state('');
	let time = $state(`${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
	let lead = $state(10);
	let busy = $state(false);

	const lineId = $derived(lines.some((l) => l.id === chosenLine) ? chosenLine : (lines[0]?.id ?? ''));
	const blocked = $derived(
		support === 'needs-home-screen'
			? 'No iPhone, toque em Compartilhar e escolha "Adicionar à Tela de Início". Abra o app por lá para receber avisos.'
			: support === 'unsupported'
				? 'Este navegador não suporta notificações push. Você ainda pode consultar os horários.'
				: support === 'supported' && permissionDenied()
					? 'As notificações estão bloqueadas neste navegador. Libere nas configurações do site para ativar alertas.'
					: ''
	);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		const line = lines.find((l) => l.id === lineId);
		if (!line || busy) return;
		busy = true;
		try {
			const identity = await subscribe();
			await api.createSubscription({
				...identity,
				stop_id: stopId,
				stop_name: stopName,
				line_id: line.id,
				line_label: line.label,
				time,
				lead_min: lead
			});
			notify('ok', `Alerta ativado para a linha ${line.label}.`);
		} catch (err) {
			notify('error', messageOf(err));
		} finally {
			busy = false;
		}
	}

	const field =
		'w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 focus:border-violet-500 dark:border-slate-700 dark:bg-slate-800';
</script>

<section class="rounded-3xl bg-white p-5 shadow-sm dark:bg-slate-900" aria-labelledby="alert-title">
	<h2 id="alert-title" class="text-lg font-extrabold">Avise-me</h2>
	<p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
		Receba uma notificação quando a linha escolhida estiver perto, no horário em que você costuma pegá-la.
	</p>

	{#if blocked}
		<p class="mt-4 rounded-2xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200" role="status">{blocked}</p>
	{/if}

	{#if lines.length === 0}
		<p class="mt-4 text-sm text-slate-500 dark:text-slate-400">Nenhuma linha passa por aqui agora. Volte quando houver previsões.</p>
	{:else}
		<form onsubmit={submit} class="mt-4 space-y-4">
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="line" class="mb-1.5 block text-sm font-bold">Linha</label>
					<select id="line" bind:value={() => lineId, (id) => (chosenLine = id)} class={field}>
						{#each lines as line (line.id)}
							<option value={line.id}>{line.label}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="time" class="mb-1.5 block text-sm font-bold">Horário aproximado</label>
					<input id="time" type="time" bind:value={time} required class={field} />
				</div>
			</div>
			<div>
				<label for="lead" class="mb-1.5 flex items-baseline justify-between text-sm font-bold">
					Avisar com antecedência
					<output for="lead" class="text-base font-extrabold text-violet-600 tabular-nums dark:text-violet-300">{lead} min</output>
				</label>
				<input id="lead" type="range" min="1" max="30" bind:value={lead} class="w-full accent-violet-600" />
			</div>
			<button
				type="submit"
				disabled={busy || support !== 'supported'}
				class="w-full rounded-2xl bg-linear-to-r from-indigo-600 to-fuchsia-600 px-6 py-3 font-extrabold text-white shadow-lg shadow-violet-500/30 transition enabled:hover:brightness-110 enabled:active:scale-[0.98] disabled:opacity-50"
			>
				{busy ? 'Ativando…' : 'Ativar alerta'}
			</button>
		</form>
	{/if}
</section>
