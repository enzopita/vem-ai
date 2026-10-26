<script lang="ts">
	import { fly } from 'svelte/transition';
	import { dismiss, toasts } from '#lib/toast.svelte.ts';
</script>

<div class="pointer-events-none fixed inset-x-0 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-50 flex flex-col items-center gap-2 px-4 md:bottom-6" aria-live="polite">
	{#each toasts as toast (toast.id)}
		<div
			in:fly={{ y: 16, duration: 220 }}
			out:fly={{ y: 16, duration: 160 }}
			class="pointer-events-auto flex w-full max-w-xl items-center gap-2 rounded-lg bg-ink py-1.5 pr-1.5 pl-4 text-[0.9375rem] font-bold text-ground shadow-[0_8px_24px_-8px_rgb(13_26_59/0.45)]"
			role={toast.kind === 'error' ? 'alert' : 'status'}
		>
			{#if toast.kind === 'error'}
				<svg viewBox="0 0 24 24" class="size-5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.5v.01" /></svg>
			{/if}
			<span class="flex-1 py-1.5">{toast.text}</span>
			{#if toast.action}
				{@const action = toast.action}
				<button
					type="button"
					class="rounded-lg px-3 underline underline-offset-4 hover:bg-ground/15"
					onclick={() => {
						action.run();
						dismiss(toast.id);
					}}>{action.label}</button
				>
			{/if}
			<button type="button" class="grid min-w-11 place-items-center rounded-lg hover:bg-ground/15" onclick={() => dismiss(toast.id)} aria-label="Fechar aviso">
				<svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
			</button>
		</div>
	{/each}
</div>
