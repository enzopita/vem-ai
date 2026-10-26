<script lang="ts">
	import type { PushSupport } from '#lib/push.ts';

	interface Props {
		support: Exclude<PushSupport, 'supported'>;
		/** Relê a permissão depois que a pessoa libera nas configurações, sem recarregar a página. */
		onrecheck?: () => void;
	}

	let { support, onrecheck }: Props = $props();
</script>

<div class="rounded-2xl bg-amber-50 p-4 text-sm text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
	{#if support === 'needs-home-screen'}
		<p class="font-bold">No iPhone, os avisos só chegam pelo app na Tela de Início.</p>
		<ol class="mt-2 list-decimal space-y-1.5 pl-5">
			<li>
				No Safari, toque em Compartilhar
				<svg viewBox="0 0 24 24" class="inline size-5 -translate-y-0.5 align-middle" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V3m0 0L8 7m4-4 4 4" /><path d="M8 11H6a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-2" /></svg>.
			</li>
			<li>Escolha "Adicionar à Tela de Início".</li>
			<li>Abra o Vem Aí pelo ícone novo e ative o alerta por lá.</li>
		</ol>
	{:else if support === 'denied'}
		<p class="font-bold">As notificações deste site estão bloqueadas, então nenhum aviso chega a este aparelho.</p>
		<ol class="mt-2 list-decimal space-y-1.5 pl-5">
			<li>Toque no ícone à esquerda do endereço do site.</li>
			<li>Em Permissões, permita as Notificações.</li>
			<li>Volte aqui e toque em "Verificar de novo".</li>
		</ol>
		{#if onrecheck}
			<button
				type="button"
				onclick={onrecheck}
				class="mt-3 rounded-xl bg-amber-900 px-4 font-semibold text-white hover:bg-amber-800 dark:bg-amber-200 dark:text-amber-950 dark:hover:bg-amber-100"
			>
				Verificar de novo
			</button>
		{/if}
	{:else}
		<p>Este navegador não recebe notificações push. Você ainda pode consultar os horários aqui.</p>
	{/if}
</div>
