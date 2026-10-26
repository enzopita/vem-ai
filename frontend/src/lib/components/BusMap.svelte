<script lang="ts">
	import type L from 'leaflet';
	import { api, type Direction, type LatLng, type LineDetail, type LiveVehicle } from '#lib/api.ts';
	import { seenClock } from '#lib/board.ts';
	import { createMap, DIRECTION_COLORS as COLORS } from '#lib/map.ts';
	import { lineLabel } from '#lib/names.ts';

	interface Props {
		line: LineDetail;
		operator: string;
		/** Prefixo do ônibus escolhido; sem ele o mapa mostra a linha toda. */
		prefix?: string;
		/** Onde a pessoa está esperando; null quando o catálogo não trouxe o ponto. */
		stop: LatLng | null;
	}

	let { line, operator, prefix, stop }: Props = $props();

	const REFRESH_MS = 15_000;
	const DIRECTIONS: Direction[] = ['ida', 'volta'];

	type Tracking =
		| { kind: 'loading' }
		| { kind: 'line'; count: number }
		| { kind: 'found'; seenAt: string }
		| { kind: 'lost' }
		| { kind: 'failed' };

	interface Layers {
		L: typeof L;
		map: L.Map;
		paths: Record<Direction, L.Polyline>;
		buses: L.LayerGroup;
	}

	let mapEl = $state<HTMLDivElement>();
	let layers = $state.raw<Layers>();
	let tracking = $state<Tracking>({ kind: 'loading' });

	$effect(() => {
		const el = mapEl;
		const detail = line;
		const here = stop;
		if (!el) return;
		let cancelled = false;
		let map: L.Map | undefined;
		(async () => {
			const base = await createMap(el, { center: [-23.95, -46.33], zoom: 12, scrollWheelZoom: false });
			map = base.map;
			if (cancelled) return map.remove();
			const { L: lf, accent } = base;
			const all: L.LatLngExpression[] = [];
			const paths = {} as Record<Direction, L.Polyline>;
			for (const d of detail.directions) {
				const pts = d.path.map((p): [number, number] => [p.lat, p.lng]);
				all.push(...pts);
				paths[d.direction] = lf.polyline(pts, { color: COLORS[d.direction], weight: 6, opacity: 0.95, lineJoin: 'round' }).addTo(map);
			}
			if (here) {
				all.push([here.lat, here.lng]);
				lf.circleMarker([here.lat, here.lng], { radius: 9, weight: 4, color: '#ffffff', fillColor: accent, fillOpacity: 1, pane: 'markerPane' })
					.bindTooltip('Seu ponto', { direction: 'top' })
					.addTo(map);
			}
			if (all.length > 0) map.fitBounds(lf.latLngBounds(all), { padding: [20, 20], animate: false });
			layers = { L: lf, map, paths, buses: lf.layerGroup().addTo(map) };
		})();
		return () => {
			cancelled = true;
			layers = undefined;
			map?.remove();
		};
	});

	function busIcon(lf: typeof L, v: LiveVehicle, selected: boolean) {
		const el = document.createElement('div');
		const color = COLORS[v.direction];
		if (selected) {
			el.textContent = v.prefix;
			el.style.cssText = `background:${color};color:#fff;border:3px solid #fff;border-radius:11px;outline:3px solid ${color};font:700 13px/22px system-ui,sans-serif;text-align:center;box-shadow:0 2px 6px rgb(0 0 0/.5)`;
			return lf.divIcon({ html: el, className: '', iconSize: [52, 28], iconAnchor: [26, 14] });
		}
		el.style.cssText = `background:${color};border:2px solid #fff;border-radius:50%;box-shadow:0 1px 3px rgb(0 0 0/.45)`;
		return lf.divIcon({ html: el, className: '', iconSize: [14, 14], iconAnchor: [7, 7] });
	}

	$effect(() => {
		const current = layers;
		const mine = prefix;
		const here = stop;
		if (!current) return;
		let ctrl: AbortController | undefined;
		let fitted = false;
		const refresh = async () => {
			ctrl?.abort();
			const attempt = (ctrl = new AbortController());
			try {
				const vehicles = await api.lineVehicles(line.id, operator, attempt.signal);
				current.buses.clearLayers();
				const chosen = mine ? vehicles.find((v) => v.prefix === mine) : undefined;
				for (const v of vehicles) {
					if (v === chosen) continue;
					current.L.marker([v.lat, v.lng], { icon: busIcon(current.L, v, false), title: `Ônibus ${v.prefix}`, zIndexOffset: 0 }).addTo(current.buses);
				}
				if (chosen) {
					current.L.marker([chosen.lat, chosen.lng], { icon: busIcon(current.L, chosen, true), title: `Ônibus ${chosen.prefix}`, zIndexOffset: 1000 }).addTo(current.buses);
				}
				// Ida e volta costumam percorrer as mesmas ruas: a de trás é mais larga para aparecer como contorno da da frente.
				const front: Direction = chosen?.direction ?? 'volta';
				for (const d of DIRECTIONS) {
					const faint = chosen !== undefined && d !== front;
					current.paths[d]?.setStyle(d === front ? { opacity: 1, weight: 4 } : { opacity: faint ? 0.4 : 0.95, weight: 9 });
				}
				current.paths[front]?.bringToFront();
				if (!fitted) {
					fitted = true;
					// A pergunta é "onde está o meu ônibus em relação ao meu ponto": enquadra os dois. A linha inteira só sem eles.
					const focus: [number, number][] = [];
					if (chosen) focus.push([chosen.lat, chosen.lng]);
					if (here) focus.push([here.lat, here.lng]);
					const pts: [number, number][] =
						chosen && here ? focus : line.directions.flatMap((d) => d.path.map((p): [number, number] => [p.lat, p.lng])).concat(focus);
					if (pts.length > 0) current.map.fitBounds(current.L.latLngBounds(pts), { padding: [40, 40], maxZoom: 16, animate: false });
				}
				tracking = !mine ? { kind: 'line', count: vehicles.length } : chosen ? { kind: 'found', seenAt: seenClock(chosen.seen_at) } : { kind: 'lost' };
			} catch {
				if (!attempt.signal.aborted) tracking = { kind: 'failed' };
			}
		};
		void refresh();
		const timer = setInterval(() => document.visibilityState === 'visible' && void refresh(), REFRESH_MS);
		const onVisible = () => document.visibilityState === 'visible' && void refresh();
		document.addEventListener('visibilitychange', onVisible);
		return () => {
			clearInterval(timer);
			document.removeEventListener('visibilitychange', onVisible);
			ctrl?.abort();
		};
	});
</script>

<div class="space-y-1.5">
	<div bind:this={mapEl} role="region" aria-label="Mapa da linha {lineLabel(line.label)}" class="h-56 w-full overflow-hidden rounded-xl border border-rule bg-quiet"></div>
	<p class="px-1 text-sm text-soft" role="status">
		{#if tracking.kind === 'found'}
			Posição às {tracking.seenAt}
		{:else if tracking.kind === 'lost'}
			Não encontramos este ônibus no rastreamento agora.
		{:else if tracking.kind === 'line'}
			{tracking.count === 0 ? 'Nenhum ônibus rastreado agora' : tracking.count === 1 ? '1 ônibus rastreado agora' : `${tracking.count} ônibus rastreados agora`}
		{:else if tracking.kind === 'failed'}
			Não conseguimos atualizar a posição agora. Tentamos de novo em instantes.
		{:else}
			Procurando o ônibus…
		{/if}
	</p>
</div>
