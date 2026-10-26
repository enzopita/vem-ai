<script lang="ts">
	import { unavailableNotice } from '#lib/operators.ts';

	let { unavailable }: { unavailable: string[] } = $props();
	const text = $derived(unavailableNotice(unavailable));
</script>

{#if text}
	<p class="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200" role="status">{text}</p>
{/if}
