<script lang="ts">
	import { unavailableNotice } from '#lib/operators.ts';

	let { unavailable }: { unavailable: string[] } = $props();
	const text = $derived(unavailableNotice(unavailable));
</script>

{#if text}
	<p class="rounded-xl bg-warn-bg px-4 py-3 text-[0.9375rem] text-warn" role="status">{text}</p>
{/if}
