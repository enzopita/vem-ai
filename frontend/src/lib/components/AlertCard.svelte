<script lang="ts">
	import type { Subscription } from '#lib/api.ts';
	import LineBadge from './LineBadge.svelte';

	interface Props {
		alert: Subscription;
		busy: boolean;
		ontest: (alert: Subscription) => void;
		ondelete: (alert: Subscription) => void;
	}

	let { alert, busy, ontest, ondelete }: Props = $props();
</script>

<article class="rounded-3xl bg-white p-4 shadow-sm dark:bg-slate-900">
	<div class="flex items-center gap-4">
		<LineBadge line={{ id: alert.line_id, label: alert.line_label }} />
		<div class="min-w-0 flex-1">
			<p class="font-bold">Linha {alert.line_label} às {alert.time}</p>
			<p class="text-sm text-slate-500 dark:text-slate-400">Avisa {alert.lead_min} min antes</p>
			<a
				href="/ponto/{encodeURIComponent(alert.stop_id)}?nome={encodeURIComponent(alert.stop_name)}"
				class="mt-1 block truncate text-sm font-medium text-violet-600 hover:underline dark:text-violet-300"
			>
				{alert.stop_name}
			</a>
		</div>
	</div>
	<div class="mt-4 grid grid-cols-2 gap-2">
		<button
			type="button"
			disabled={busy}
			onclick={() => ontest(alert)}
			class="rounded-2xl bg-violet-50 px-4 font-bold text-violet-700 hover:bg-violet-100 disabled:opacity-50 dark:bg-violet-950/50 dark:text-violet-200 dark:hover:bg-violet-950"
		>
			Testar
		</button>
		<button
			type="button"
			disabled={busy}
			onclick={() => ondelete(alert)}
			class="rounded-2xl bg-rose-50 px-4 font-bold text-rose-700 hover:bg-rose-100 disabled:opacity-50 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-950"
		>
			Excluir
		</button>
	</div>
</article>
