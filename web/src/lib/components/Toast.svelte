<script lang="ts">
	import { fly } from 'svelte/transition';
	import { dismiss, toasts, type ToastKind } from '#lib/toast.svelte.ts';

	const tone: Record<ToastKind, string> = {
		ok: 'bg-emerald-600 text-white',
		error: 'bg-rose-600 text-white',
		info: 'bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900'
	};
</script>

<div
	class="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex flex-col items-center gap-2 px-4 md:bottom-6"
	aria-live="polite"
>
	{#each toasts as toast (toast.id)}
		<div
			in:fly={{ y: 24, duration: 220 }}
			out:fly={{ y: 24, duration: 180 }}
			class="pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-2xl py-2 pr-2 pl-4 text-sm font-medium shadow-xl {tone[toast.kind]}"
			role={toast.kind === 'error' ? 'alert' : 'status'}
		>
			<span class="flex-1 py-1">{toast.text}</span>
			<button
				type="button"
				class="grid min-w-11 place-items-center rounded-xl text-lg opacity-80 hover:bg-white/15"
				onclick={() => dismiss(toast.id)}
				aria-label="Fechar aviso">×</button
			>
		</div>
	{/each}
</div>
