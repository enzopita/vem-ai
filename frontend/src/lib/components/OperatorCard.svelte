<script lang="ts">
	import type { Operator } from '#lib/api.ts';

	interface Props {
		operator: Operator;
		selected: boolean;
		onselect: (name: string) => void;
	}

	let { operator, selected, onselect }: Props = $props();

	const labels: Record<string, string> = { piracicabana: 'Piracicabana', brmobilidadebs: 'BR Mobilidade' };
	const label = $derived(labels[operator.name] ?? operator.name);
</script>

<button
	type="button"
	disabled={!operator.online}
	aria-pressed={selected}
	onclick={() => onselect(operator.name)}
	class="group flex min-h-20 w-full items-center gap-3 rounded-3xl border-2 p-4 text-left shadow-sm transition-all enabled:hover:-translate-y-0.5 enabled:hover:shadow-md disabled:opacity-60
		{selected
		? 'border-violet-500 bg-violet-50 shadow-violet-500/20 dark:border-violet-400 dark:bg-violet-950/50'
		: 'border-transparent bg-slate-50 dark:bg-slate-800'}"
>
	<span
		class="grid size-12 shrink-0 place-items-center rounded-2xl bg-linear-to-br from-indigo-500 to-fuchsia-500 text-lg font-extrabold text-white"
		aria-hidden="true">{label[0]}</span
	>
	<span class="min-w-0 flex-1">
		<span class="block truncate font-bold">{label}</span>
		<span class="mt-0.5 flex items-center gap-1.5 text-sm {operator.online ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500'}">
			<span class="relative flex size-2.5">
				{#if operator.online}
					<span class="absolute inline-flex size-full animate-ping-soft rounded-full bg-emerald-500"></span>
				{/if}
				<span class="relative inline-flex size-2.5 rounded-full {operator.online ? 'bg-emerald-500' : 'bg-slate-400'}"></span>
			</span>
			{operator.online ? 'Online' : 'Offline no momento'}
		</span>
	</span>
	{#if selected}
		<svg viewBox="0 0 24 24" class="size-6 text-violet-600 dark:text-violet-300" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
	{/if}
</button>
