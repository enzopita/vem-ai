<script lang="ts">
	import type { Line } from '#lib/api.ts';
	import { etaScale, type LineGroup } from '#lib/board.ts';
	import { personName, lineLabel } from '#lib/names.ts';
	import { kindSuffix } from '#lib/operators.ts';
	import LineTile from './LineTile.svelte';

	interface Props {
		group: LineGroup;
		/** A leitura é a última que deu certo, não a atual: nada pode parecer ao vivo. */
		stale: boolean;
		onbus: (group: LineGroup) => void;
		onalert: (line: Line) => void;
	}

	let { group, stale, onbus, onalert }: Props = $props();
	const first = $derived(group.arrivals[0]);
	const arriving = $derived(first.eta === 0);
	// Fundo verde quer dizer "chegando agora"; numa leitura antiga a linha só fica contornada.
	const live = $derived(arriving && !stale);
	const later = $derived(group.arrivals.slice(1));
	// Só o próximo depois do primeiro: a coluna do tempo é estreita, e a folha do ônibus mostra o resto.
	const trailing = $derived(later.length === 0 ? '' : later[0].eta === 0 ? 'outro chegando' : `depois ${later[0].eta} min`);
</script>

<div
	class="relative isolate flex items-stretch overflow-hidden transition-colors duration-500 {live ? '' : 'bg-surface'} {stale
		? `outline-2 -outline-offset-4 outline-dashed ${arriving ? 'outline-ok' : 'outline-soft'}`
		: ''}"
>
	<!-- O verde tinge a linha de baixo para cima quando o ônibus chega: o único movimento autoral do app. -->
	<span
		class="absolute inset-0 -z-10 origin-bottom bg-ok-bg transition-transform duration-500 ease-out-expo {live ? 'scale-y-100' : 'scale-y-0'}"
		aria-hidden="true"
	></span>
	<button
		type="button"
		onclick={() => onbus(group)}
		class="flex min-h-11 min-w-0 flex-1 items-center gap-3 py-1.5 pr-1 pl-3 text-left focus-visible:-outline-offset-4 {live ? '' : 'hover:bg-quiet'}"
	>
	<!-- Uma faixa por linha, em colunas fixas: placa, tempo, quem vem. Cabem quase o dobro de linhas na tela. -->
	<span class="flex w-12 shrink-0"><LineTile label={group.line.label} operator={group.line.operator} size="sm" /></span>
	<span class="sr-only">Linha {lineLabel(group.line.label)}{kindSuffix(group.line.operator)}:</span>
	<!-- Prefixo e motorista empilhados, cada um com seu ícone: sem ícone, "4422 · Josimar" não diz o que é cada parte. -->
	<span class="min-w-0 flex-1 space-y-0.5 text-sm leading-tight">
		{#if first.vehicle}
			<span class="flex items-center gap-1.5">
				<svg viewBox="0 0 24 24" class="size-4 shrink-0 text-soft" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 6v6" /><path d="M15 6v6" /><path d="M2 12h19.6" /><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3" /><circle cx="7" cy="18" r="2" /><path d="M9 18h5" /><circle cx="16" cy="18" r="2" /></svg>
				<span class="truncate"><span class="sr-only">. Ônibus </span>{first.vehicle}</span>
			</span>
		{/if}
		{#if first.driver}
			<span class="flex items-center gap-1.5 text-soft">
				<svg viewBox="0 0 24 24" class="size-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
				<span class="truncate"><span class="sr-only">, motorista </span>{personName(first.driver)}</span>
			</span>
		{/if}
	</span>
	<span class="w-24 shrink-0 text-right leading-none whitespace-nowrap">
		{#if arriving}
			<span class="text-base font-bold tracking-tight text-ok">Chegando</span>
		{:else}
			<span class={stale ? 'text-soft' : ''}>
				<span class="font-bold tracking-tight {etaScale(first.eta)}">{first.eta}</span>
				<span class="ml-0.5 text-sm font-semibold text-soft">min</span>
			</span>
		{/if}
		{#if trailing}<span class="mt-1 block truncate text-xs text-soft"><span class="sr-only">. </span>{trailing}</span>{/if}
	</span>
	</button>
	<button
		type="button"
		onclick={() => onalert(group.line)}
		aria-label="Avisar da linha {lineLabel(group.line.label)}"
		class="grid w-11 shrink-0 place-items-center {live ? 'text-ok' : 'text-soft hover:bg-quiet'} focus-visible:-outline-offset-4"
	>
		<svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0" /></svg>
	</button>
</div>
