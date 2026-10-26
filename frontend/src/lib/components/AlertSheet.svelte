<script lang="ts">
	import { api, messageOf, type Line } from '#lib/api.ts';
	import { PermissionDeniedError, pushSupport, subscribe, willAskPermission } from '#lib/push.ts';
	import { notify } from '#lib/toast.svelte.ts';
	import { stopLabel, lineLabel } from '#lib/names.ts';
	import LineTile from './LineTile.svelte';
	import PushHelp from './PushHelp.svelte';

	interface Props {
		stopId: string;
		stopName: string;
		/** A linha tocada no quadro; null fecha a folha. */
		line: Line | null;
		onclose: () => void;
	}

	let { stopId, stopName, line, onclose }: Props = $props();

	// As previsões só vão até 20 min, então antecedência maior que isso nunca dispararia.
	const LEADS = [5, 10, 15, 20];

	const nowHHMM = () => {
		const now = new Date();
		return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
	};

	let dialog: HTMLDialogElement;
	let title = $state<HTMLHeadingElement>();
	let support = $state(pushSupport());
	let asking = $state(willAskPermission());
	let time = $state(nowHHMM());
	let lead = $state(10);
	let busy = $state(false);

	$effect(() => {
		if (line) {
			support = pushSupport();
			asking = willAskPermission();
			time = nowHHMM();
			if (!dialog.open) {
				dialog.showModal();
				// O foco começa no título para o leitor de tela anunciar a folha, sem anel no botão de fechar.
				title?.focus();
			}
		} else if (dialog.open) {
			dialog.close();
		}
	});

	function recheck() {
		support = pushSupport();
		asking = willAskPermission();
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
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
				line_operator: line.operator ?? '',
				time,
				lead_min: lead
			});
			notify('ok', `Alerta ativado: linha ${lineLabel(line.label)} por volta das ${time}.`);
			dialog.close();
		} catch (err) {
			if (err instanceof PermissionDeniedError) {
				recheck();
				// Negado vira o bloco fixo acima; pedido fechado sem resposta pode ser refeito no próximo toque.
				if (support === 'supported') notify('info', err.message);
			} else {
				notify('error', messageOf(err));
			}
		} finally {
			busy = false;
		}
	}

	const field = 'w-full rounded-lg border border-rule bg-surface px-4 text-lg focus:border-accent';
</script>

<dialog
	bind:this={dialog}
	class="folha"
	aria-labelledby="alert-title"
	{onclose}
	onclick={(e) => e.target === dialog && dialog.close()}
>
	{#if line}
		<form onsubmit={submit} class="space-y-5 p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
			<header class="flex items-center gap-3">
				<LineTile label={line.label} operator={line.operator} />
				<div class="min-w-0 flex-1">
					<h2 id="alert-title" bind:this={title} tabindex="-1" class="text-xl leading-tight font-bold outline-none">Avisar da linha {lineLabel(line.label)}</h2>
					<p class="truncate text-[0.9375rem] text-soft">{stopLabel(stopName)}</p>
				</div>
				<button type="button" onclick={() => dialog.close()} aria-label="Fechar" class="grid min-w-11 place-items-center rounded-lg text-soft hover:bg-quiet">
					<svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
				</button>
			</header>

			<div aria-live="polite">
				{#if support !== 'supported'}
					<PushHelp {support} onrecheck={recheck} />
				{/if}
			</div>

			<div>
				<label for="alert-time" class="mb-1.5 block font-bold">Horário em que você costuma pegar</label>
				<input id="alert-time" type="time" bind:value={time} required class={field} />
			</div>

			<fieldset>
				<legend class="mb-1.5 font-bold">Avisar quando faltar</legend>
				<div class="grid grid-cols-4 gap-2">
					{#each LEADS as minutes (minutes)}
						<label
							class="grid min-h-12 cursor-pointer place-items-center rounded-lg border border-rule font-bold has-checked:border-accent has-checked:bg-accent has-checked:text-on-accent has-focus-visible:outline-3 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent has-focus-visible:outline-solid"
						>
							<input type="radio" name="lead" value={minutes} bind:group={lead} class="sr-only" />
							{minutes} min
						</label>
					{/each}
				</div>
			</fieldset>

			<p class="text-[0.9375rem] text-soft">
				Vigiamos a linha de 30 min antes a 30 min depois desse horário. Se o ônibus sumir do rastreamento, também avisamos.
			</p>

			{#if asking && support === 'supported'}
				<p id="permission-hint" class="text-[0.9375rem] text-soft">
					Na primeira vez, o navegador vai pedir permissão para mostrar notificações. Toque em "Permitir" para receber o aviso.
				</p>
			{/if}

			<button
				type="submit"
				aria-describedby={asking && support === 'supported' ? 'permission-hint' : undefined}
				disabled={busy || support !== 'supported'}
				class="w-full rounded-lg bg-accent px-6 py-3 text-lg font-bold text-on-accent transition enabled:hover:brightness-110 enabled:active:translate-y-px disabled:opacity-45"
			>
				{busy ? 'Ativando…' : 'Ativar alerta'}
			</button>
		</form>
	{/if}
</dialog>
