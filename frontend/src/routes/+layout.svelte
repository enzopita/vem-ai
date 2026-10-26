<script lang="ts">
	import { page } from '$app/state';
	import InstallBanner from '#lib/components/InstallBanner.svelte';
	import Toast from '#lib/components/Toast.svelte';
	import { cycleTheme, theme, type ThemeChoice } from '#lib/theme.svelte.ts';
	import '../app.css';

	let { children } = $props();

	// Campo de digitação em foco = teclado aberto no celular. A barra fixa de baixo sobe junto com ele e rouba a
	// altura em que a pessoa está rolando os resultados, então ela some enquanto alguém digita.
	const TYPING = 'input:not([type=radio]):not([type=checkbox]):not([type=button]):not([type=submit]), textarea';
	let typing = $state(false);
	const onFocusIn = (e: FocusEvent) => (typing = e.target instanceof Element && e.target.matches(TYPING));
	const onFocusOut = () => (typing = false);

	const THEME_LABEL: Record<ThemeChoice, string> = { system: 'igual ao sistema', light: 'claro', dark: 'escuro' };

	const tabs = [
		{ href: '/', label: 'Início', match: (p: string) => p === '/' || p.startsWith('/ponto') || p.startsWith('/linha'), icon: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z' },
		{ href: '/alertas', label: 'Alertas', match: (p: string) => p.startsWith('/alertas'), icon: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0' }
	];
</script>

<svelte:head><title>Vem Aí</title></svelte:head>

<div class="flex min-h-dvh flex-col pt-[env(safe-area-inset-top)] pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0">
	<header class="calcadao border-b border-rule bg-surface">
		<div class="mx-auto flex max-w-xl items-center justify-between px-4 py-2">
			<a href="/" class="-ml-1 flex items-center gap-2 rounded-lg px-1 text-lg font-bold tracking-tight">
				<img src="/icon.svg" alt="" class="size-8" />
				Vem Aí
			</a>
			<div class="flex items-center gap-1">
				<nav class="hidden gap-1 md:flex" aria-label="Principal">
					{#each tabs as tab (tab.href)}
						{@const active = tab.match(page.url.pathname)}
						<a
							href={tab.href}
							aria-current={active ? 'page' : undefined}
							class="flex items-center rounded-lg px-3 text-[0.9375rem] font-semibold {active ? 'bg-quiet text-ink' : 'text-soft hover:bg-quiet hover:text-ink'}"
						>
							{tab.label}
						</a>
					{/each}
				</nav>
				<button
					type="button"
					onclick={cycleTheme}
					aria-label="Tema {THEME_LABEL[theme.choice]}. Toque para trocar."
					title="Tema {THEME_LABEL[theme.choice]}"
					class="grid min-h-11 min-w-11 place-items-center rounded-lg text-soft hover:bg-quiet hover:text-ink"
				>
					<svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
						{#if theme.choice === 'light'}
							<circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
						{:else if theme.choice === 'dark'}
							<path d="M20.5 14.3A8.5 8.5 0 0 1 9.7 3.5a8.5 8.5 0 1 0 10.8 10.8z" />
						{:else}
							<rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" />
						{/if}
					</svg>
				</button>
			</div>
		</div>
	</header>
	<InstallBanner />

	<main class="mx-auto w-full max-w-xl flex-1 px-4 pt-3 pb-4">
		{@render children()}
	</main>

</div>

<svelte:window onfocusin={onFocusIn} onfocusout={onFocusOut} />

<nav class="fixed inset-x-0 bottom-0 z-40 border-t border-rule bg-surface pb-[env(safe-area-inset-bottom)] md:hidden {typing ? 'hidden' : ''}" aria-label="Principal">
	<div class="mx-auto grid max-w-md grid-cols-2">
		{#each tabs as tab (tab.href)}
			{@const active = tab.match(page.url.pathname)}
			<a
				href={tab.href}
				aria-current={active ? 'page' : undefined}
				class="relative flex min-h-16 flex-col items-center justify-center gap-0.5 text-[0.8125rem] font-semibold {active ? 'text-accent' : 'text-soft'}"
			>
				{#if active}<span class="absolute inset-x-10 top-0 h-0.5 rounded-b bg-accent" aria-hidden="true"></span>{/if}
				<svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={tab.icon} /></svg>
				{tab.label}
			</a>
		{/each}
	</div>
</nav>

<Toast />
