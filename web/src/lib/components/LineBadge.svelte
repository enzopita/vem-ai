<script lang="ts">
	import type { Line } from '#lib/api.ts';

	let { line, small = false }: { line: Line; small?: boolean } = $props();

	// O mesmo id sempre dá a mesma cor, então a linha é reconhecível de relance.
	const hue = $derived([...line.id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7));
</script>

<span
	class="inline-grid shrink-0 place-items-center rounded-2xl font-extrabold text-white shadow-sm {small ? 'h-9 min-w-9 px-2 text-sm' : 'h-14 min-w-14 px-2 text-xl'}"
	style="background: linear-gradient(135deg, hsl({hue} 70% 42%), hsl({(hue + 40) % 360} 70% 36%))"
>
	{line.label}
</span>
