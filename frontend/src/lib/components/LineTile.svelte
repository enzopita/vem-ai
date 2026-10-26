<script lang="ts">
	import { lineLabel } from '#lib/names.ts';
	import { lineKind, type LineKind } from '#lib/operators.ts';

	interface Props {
		label: string;
		operator?: string;
		size?: 'lg' | 'sm';
	}

	let { label: raw, operator, size = 'lg' }: Props = $props();
	const label = $derived(lineLabel(raw));
	// Largura fixa alinha a coluna; rótulos longos ("CIRCULAR 139") quebram em duas linhas, nunca abaixo de 13px.
	const long = $derived(label.length > 4);
	// Verde é municipal e azul é intermunicipal, como nos ônibus da Baixada.
	const TONES: Record<LineKind, string> = { municipal: 'bg-municipal', intermunicipal: 'bg-intermunicipal' };
	const tone = $derived.by(() => {
		const kind = lineKind(operator);
		return kind ? TONES[kind] : 'bg-linha-outra';
	});
</script>

<span
	class="inline-grid shrink-0 place-items-center rounded-lg text-center font-bold text-white {tone} {size === 'lg'
		? `h-10 w-[4.75rem] px-1 ${long ? 'text-[0.8125rem] leading-[1.05]' : 'text-lg'}`
		: `h-7 px-1.5 ${long ? 'min-w-14 text-[0.8125rem] whitespace-nowrap' : 'min-w-10 text-sm'}`}"
	aria-hidden="true"
>
	{label}
</span>
