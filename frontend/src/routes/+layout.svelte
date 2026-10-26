<script lang="ts">
	import { page } from '$app/state';
	import Toast from '#lib/components/Toast.svelte';
	import '../app.css';

	let { children } = $props();
	const home = $derived(page.url.pathname === '/');

	const tabs = [
		{ href: '/', label: 'Início', match: (p: string) => p === '/' || p.startsWith('/ponto'), icon: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z' },
		{ href: '/alertas', label: 'Alertas', match: (p: string) => p.startsWith('/alertas'), icon: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0' }
	];
</script>

<svelte:head><title>Vem Aí</title></svelte:head>

<div class="min-h-dvh pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:pb-12">
	<div class="bg-linear-to-br from-indigo-600 via-violet-600 to-fuchsia-600 pt-[env(safe-area-inset-top)] text-white dark:from-indigo-900 dark:via-violet-900 dark:to-fuchsia-900 {home ? 'pb-16' : 'pb-10'}">
	<header>
		<div class="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
			<a href="/" class="flex items-center gap-2.5 rounded-xl text-xl font-extrabold tracking-tight">
				<img src="/icon.svg" alt="" class="size-9 rounded-xl shadow-md" />
				Vem Aí
			</a>
			<nav class="hidden gap-1 md:flex" aria-label="Principal">
				{#each tabs as tab (tab.href)}
					{@const active = tab.match(page.url.pathname)}
					<a
						href={tab.href}
						aria-current={active ? 'page' : undefined}
						class="flex items-center rounded-xl px-4 text-sm font-semibold transition-colors {active ? 'bg-white/20' : 'hover:bg-white/10'}"
					>
						{tab.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>
	{#if home}
		<section class="mx-auto max-w-3xl px-4 pt-4">
			<h1 class="text-3xl leading-tight font-extrabold tracking-tight text-balance md:text-4xl">O ônibus vem aí.<br />Você só espera sentado.</h1>
			<p class="mt-2 max-w-md text-white/85">Escolha o ponto e a linha. Avisamos no celular quando o ônibus estiver chegando.</p>
		</section>
	{/if}
	</div>

	<main class="mx-auto -mt-8 max-w-3xl px-4">
		{@render children()}
	</main>
</div>

<nav
	class="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden dark:border-slate-800 dark:bg-slate-900/90"
	aria-label="Principal"
>
	<div class="mx-auto grid max-w-md grid-cols-2">
		{#each tabs as tab (tab.href)}
			{@const active = tab.match(page.url.pathname)}
			<a
				href={tab.href}
				aria-current={active ? 'page' : undefined}
				class="flex min-h-16 flex-col items-center justify-center gap-0.5 text-xs font-semibold transition-colors {active ? 'text-violet-600 dark:text-violet-400' : 'text-slate-500 dark:text-slate-400'}"
			>
				<svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={tab.icon} /></svg>
				{tab.label}
			</a>
		{/each}
	</div>
</nav>

<Toast />
