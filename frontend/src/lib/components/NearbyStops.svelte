<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { messageOf, type CatalogStop } from '#lib/api.ts';
	import { loadCatalog as fetchCatalog } from '#lib/catalog.ts';
	import { nearest, formatDistance, type Coord } from '#lib/geo.ts';
	import { stopLabel } from '#lib/names.ts';
	import { createMap, stopMarker } from '#lib/map.ts';
	import { stopHref } from '#lib/recent.ts';
	import UnavailableNotice from './UnavailableNotice.svelte';

	type Location =
		| { kind: 'idle' }
		| { kind: 'locating' }
		| { kind: 'located'; here: Coord }
		| { kind: 'denied' }
		| { kind: 'unsupported' }
		| { kind: 'failed' };

	type Catalog =
		| { kind: 'loading' }
		| { kind: 'ready'; stops: CatalogStop[] }
		| { kind: 'building' }
		| { kind: 'failed'; message: string };

	const MAP_STOPS = 20;
	const LIST_STOPS = 5;

	let location = $state<Location>({ kind: 'idle' });
	let catalog = $state<Catalog>({ kind: 'loading' });
	let unavailable = $state<string[]>([]);
	let mapEl = $state<HTMLDivElement>();

	const here = $derived(location.kind === 'located' ? location.here : null);
	const near = $derived(here && catalog.kind === 'ready' ? nearest(catalog.stops, here, MAP_STOPS) : []);

	function locate() {
		if (!('geolocation' in navigator)) {
			location = { kind: 'unsupported' };
			return;
		}
		location = { kind: 'locating' };
		navigator.geolocation.getCurrentPosition(
			(pos) => (location = { kind: 'located', here: { lat: pos.coords.latitude, lng: pos.coords.longitude } }),
			(err) => (location = err.code === err.PERMISSION_DENIED ? { kind: 'denied' } : { kind: 'failed' }),
			{ enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 }
		);
	}

	async function loadCatalog(signal?: AbortSignal) {
		catalog = { kind: 'loading' };
		try {
			const found = await fetchCatalog();
			if (signal?.aborted) return;
			unavailable = found.unavailable;
			catalog = found.stops.length > 0 ? { kind: 'ready', stops: found.stops } : { kind: 'building' };
		} catch (err) {
			if (signal?.aborted) return;
			catalog = { kind: 'failed', message: messageOf(err) };
		}
	}

	onMount(() => {
		// Só localiza sozinho quando a permissão já foi dada; pedir ao abrir a página assusta.
		navigator.permissions
			?.query({ name: 'geolocation' })
			.then((p) => {
				if (p.state === 'granted') locate();
			})
			.catch(() => {});
	});

	// O catálogo só pesa quando a pessoa pede os pontos perto dela.
	$effect(() => {
		if (location.kind !== 'located') return;
		const ctrl = new AbortController();
		loadCatalog(ctrl.signal);
		return () => ctrl.abort();
	});

	$effect(() => {
		const el = mapEl;
		const center = here;
		const stops = near;
		if (!el || !center) return;
		let cancelled = false;
		let teardown = () => {};
		(async () => {
			const { L, map, accent } = await createMap(el, { center: [center.lat, center.lng], zoom: 16 });
			if (cancelled) {
				map.remove();
				return;
			}

			for (const stop of stops) {
				const marker = stopMarker(L, [stop.lat, stop.lng], accent).addTo(map);
				const box = document.createElement('div');
				const name = document.createElement('p');
				name.className = 'font-semibold';
				name.textContent = stopLabel(stop.name);
				const link = document.createElement('a');
				link.href = stopHref(stop);
				link.className = 'mt-1 block font-semibold';
				link.style.color = '#0a5fc4';
				link.textContent = 'Abrir o ponto';
				link.addEventListener('click', (e) => {
					e.preventDefault();
					goto(link.href);
				});
				box.append(name, link);
				marker.bindPopup(box);
			}
			L.circleMarker([center.lat, center.lng], { radius: 9, weight: 3, color: '#ffffff', fillColor: accent, fillOpacity: 1, interactive: false }).addTo(map);

			if (stops.length > 0) {
				const bounds = L.latLngBounds([[center.lat, center.lng], ...stops.slice(0, 8).map((s): [number, number] => [s.lat, s.lng])]);
				map.fitBounds(bounds, { padding: [24, 24], maxZoom: 17, animate: false });
			}
			teardown = () => map.remove();
		})();
		return () => {
			cancelled = true;
			teardown();
		};
	});
</script>

<section aria-labelledby="perto-title" class="space-y-2">
	<h2 id="perto-title" class="px-1 text-sm font-semibold text-soft">Pontos perto de você</h2>

	{#if location.kind === 'idle'}
		<button type="button" onclick={locate} class="min-h-12 w-full rounded-xl bg-accent px-4 font-semibold text-on-accent">Mostrar pontos perto de mim</button>
		<p class="px-1 text-[0.8125rem] text-soft">Sua posição fica só no seu aparelho.</p>
	{:else if location.kind === 'locating'}
		<p class="px-1 text-soft" role="status">Descobrindo onde você está…</p>
	{:else if location.kind === 'denied'}
		<div class="flex items-center gap-3 rounded-xl border border-rule bg-surface py-2 pr-2 pl-4 text-[0.9375rem]">
			<p class="min-w-0 flex-1 text-soft"><span class="font-semibold text-ink">Localização bloqueada.</span> Permita no navegador para ver os pontos perto.</p>
			<button type="button" onclick={locate} class="min-h-11 shrink-0 rounded-lg border border-rule bg-quiet px-3 font-semibold">Tentar de novo</button>
		</div>
	{:else if location.kind === 'unsupported'}
		<p class="px-1 text-[0.9375rem] text-soft">Este navegador não tem localização. Use a busca acima.</p>
	{:else if location.kind === 'failed'}
		<div class="space-y-2 rounded-xl border border-rule bg-surface px-4 py-3 text-[0.9375rem]">
			<p class="text-soft">Não conseguimos descobrir onde você está. Confira o GPS e tente de novo.</p>
			<button type="button" onclick={locate} class="min-h-11 rounded-lg border border-rule bg-quiet px-4 font-semibold">Tentar de novo</button>
		</div>
	{:else if catalog.kind === 'loading'}
		<div class="h-48 animate-shimmer rounded-xl border border-rule bg-surface" aria-hidden="true"></div>
		<p class="sr-only" role="status">Carregando os pontos…</p>
	{:else if catalog.kind === 'building'}
		<p class="rounded-xl border border-rule bg-surface px-4 py-3 text-[0.9375rem] text-soft" role="status">Estamos montando o mapa de pontos da região. Volte em alguns minutos.</p>
	{:else if catalog.kind === 'failed'}
		<div class="space-y-2 rounded-xl bg-danger-bg p-3 text-[0.9375rem] text-danger">
			<p>{catalog.message}</p>
			<button type="button" onclick={() => loadCatalog()} class="min-h-11 rounded-lg bg-surface px-4 font-semibold text-ink">Tentar de novo</button>
		</div>
	{:else}
		{#if unavailable.length > 0}<UnavailableNotice {unavailable} />{/if}
		<div bind:this={mapEl} role="region" aria-label="Mapa dos pontos perto de você" class="h-48 w-full overflow-hidden rounded-xl border border-rule bg-quiet shadow-card"></div>
		<ul class="painel">
			{#each near.slice(0, LIST_STOPS) as stop (stop.id)}
				<li>
					<a href={stopHref(stop)} class="flex items-center gap-3 bg-surface px-4 py-2 hover:bg-quiet focus-visible:-outline-offset-4">
						<span class="min-w-14 rounded-md bg-quiet px-2 py-0.5 text-center text-sm font-semibold text-soft">{stop.id}</span>
						<span class="min-w-0 flex-1 font-semibold">{stopLabel(stop.name)}</span>
						<span class="shrink-0 text-[0.9375rem] text-soft tabular-nums">{formatDistance(stop.distance)}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</section>
