<script lang="ts">
	import type { Subscription } from '#lib/api.ts';
	import { stopLabel, lineLabel } from '#lib/names.ts';
	import { stopHref } from '#lib/recent.ts';
	import LineTile from './LineTile.svelte';

	interface Props {
		alert: Subscription;
		busy: boolean;
		ontest: (alert: Subscription) => void;
		ondelete: (alert: Subscription) => void;
	}

	let { alert, busy, ontest, ondelete }: Props = $props();
</script>

<article class="rounded-xl border border-rule bg-surface p-4 shadow-card">
	<div class="flex items-start gap-3">
		<LineTile label={lineLabel(alert.line_label)} operator={alert.line_operator} />
		<div class="min-w-0 flex-1">
			<h2 class="text-lg leading-snug font-bold">Linha {lineLabel(alert.line_label)}, por volta das {alert.time}</h2>
			<p class="text-[0.9375rem] text-soft">Avisa quando faltar {alert.lead_min} min</p>
			<a href={stopHref({ id: alert.stop_id, name: alert.stop_name })} class="-mx-1 block truncate rounded-lg px-1 leading-[2.75rem] font-semibold text-accent hover:underline">
				{stopLabel(alert.stop_name)}
			</a>
		</div>
	</div>
	<div class="mt-2 flex items-center gap-2 border-t-2 border-rule pt-3">
		<button
			type="button"
			disabled={busy}
			onclick={() => ontest(alert)}
			class="rounded-lg border border-accent px-4 font-bold text-accent hover:bg-quiet disabled:opacity-50"
		>
			Enviar teste
		</button>
		<button
			type="button"
			disabled={busy}
			onclick={() => ondelete(alert)}
			class="ml-auto rounded-lg px-3 font-bold text-danger hover:bg-danger-bg disabled:opacity-50"
		>
			Excluir
		</button>
	</div>
</article>
