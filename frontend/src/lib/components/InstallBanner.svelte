<script lang="ts">
	import { slide } from 'svelte/transition';
	import { dismissInstall, install, promptInstall } from '#lib/install.svelte.ts';

	const android = /android/i.test(navigator.userAgent);
	// O passo a passo só aparece para quem pede: fechado, a faixa ocupa uma linha.
	let howOpen = $state(false);
</script>

{#if install.offer !== 'none'}
	<aside transition:slide={{ duration: 200 }} aria-label="Instalar o app" class="border-b border-rule bg-surface">
		<div class="mx-auto flex max-w-xl items-center gap-2 px-4 py-1">
			<img src="/icon.svg" alt="" class="size-6 shrink-0" />
			<p class="min-w-0 flex-1 truncate text-sm font-semibold">Instale o Vem Aí</p>
			{#if install.offer === 'prompt'}
				<button type="button" onclick={promptInstall} class="min-h-9 shrink-0 rounded-lg bg-accent px-3 text-sm font-semibold text-on-accent hover:brightness-110">Instalar</button>
			{:else}
				<button type="button" onclick={() => (howOpen = !howOpen)} aria-expanded={howOpen} aria-controls="install-how" class="min-h-9 shrink-0 rounded-lg px-2 text-sm font-semibold text-accent hover:bg-quiet">Como instalar</button>
			{/if}
			<button type="button" onclick={dismissInstall} aria-label="Agora não" class="grid min-h-11 min-w-11 shrink-0 place-items-center rounded-lg text-soft hover:bg-quiet">
				<svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
			</button>
		</div>
		{#if howOpen && install.offer !== 'prompt'}
			<p id="install-how" transition:slide={{ duration: 150 }} class="mx-auto max-w-xl px-4 pb-2 text-sm text-soft">
				{#if install.offer === 'ios'}
					No Safari, toque em Compartilhar
					<svg viewBox="0 0 24 24" class="inline size-4 -translate-y-px align-middle" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="(ícone de compartilhar)"><path d="M12 15V3m0 0L8 7m4-4 4 4" /><path d="M8 11H6a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-2" /></svg>
					e em "Adicionar à Tela de Início". No iPhone os avisos só chegam assim; em outro navegador, como o Brave, abra este endereço no Safari.
				{:else if android}
					Toque em ⋮ no canto do navegador e escolha "Instalar app" ou "Adicionar à tela inicial".
				{:else}
					Use o ícone de instalar na barra de endereço ou o menu do navegador.
				{/if}
			</p>
		{/if}
	</aside>
{/if}
