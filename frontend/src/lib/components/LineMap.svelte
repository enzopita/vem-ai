<script lang="ts">
	import type L from 'leaflet';
	import { api, type Direction, type LineDetail, type LiveVehicle } from '#lib/api.ts';
	import { clock, seenClock } from '#lib/board.ts';
	import { createMap, DIRECTION_COLORS as COLORS, stopMarker } from '#lib/map.ts';
	import { personName, stopLabel, lineLabel } from '#lib/names.ts';

	interface Props {
		line: LineDetail;
		operator: string;
	}

	let { line, operator }: Props = $props();

	const REFRESH_MS = 15_000;
	const directionName = (d: Direction) => line.directions.find((x) => x.direction === d)?.name ?? '';

	interface Layers {
		L: typeof L;
		map: L.Map;
		buses: L.LayerGroup;
	}

	let mapEl = $state<HTMLDivElement>();
	let layers = $state.raw<Layers>();
	let status = $state<{ at: Date; count: number } | null>(null);
	let failed = $state(false);

	$effect(() => {
		const el = mapEl;
		const detail = line;
		if (!el) return;
		let cancelled = false;
		let map: L.Map | undefined;
		(async () => {
			const base = await createMap(el, { center: [-23.95, -46.33], zoom: 12 });
			map = base.map;
			if (cancelled) return map.remove();
			const { L: lf, accent } = base;
			const all: L.LatLngExpression[] = [];
			for (const d of detail.directions) {
				const pts = d.path.map((p): [number, number] => [p.lat, p.lng]);
				all.push(...pts);
				lf.polyline(pts, { color: COLORS[d.direction], weight: 5, opacity: 0.85, lineJoin: 'round' }).addTo(map);
			}
			for (const s of detail.stops) {
				const m = stopMarker(lf, [s.lat, s.lng], accent).addTo(map);
				m.bindTooltip(stopLabel(s.name), { direction: 'top' });
			}
			if (all.length > 0) map.fitBounds(lf.latLngBounds(all), { padding: [20, 20], animate: false });
			layers = { L: lf, map, buses: lf.layerGroup().addTo(map) };
		})();
		return () => {
			cancelled = true;
			layers = undefined;
			map?.remove();
		};
	});

	function busIcon(lf: typeof L, v: LiveVehicle) {
		const el = document.createElement('div');
		el.textContent = v.prefix;
		el.style.cssText = `background:${COLORS[v.direction]};color:#fff;border:2px solid #fff;border-radius:9px;font:700 12px/20px system-ui,sans-serif;text-align:center;box-shadow:0 1px 4px rgb(0 0 0/.45)`;
		return lf.divIcon({ html: el, className: '', iconSize: [42, 24], iconAnchor: [21, 12], popupAnchor: [0, -12] });
	}

	function popup(v: LiveVehicle) {
		const parts = [`Ônibus ${v.prefix}`, v.driver && personName(v.driver), directionName(v.direction) && `Sentido ${directionName(v.direction)}`, `posição às ${seenClock(v.seen_at)}`];
		const p = document.createElement('p');
		p.textContent = parts.filter(Boolean).join(' · ');
		return p;
	}

	$effect(() => {
		const current = layers;
		if (!current) return;
		let ctrl: AbortController | undefined;
		const refresh = async () => {
			ctrl?.abort();
			const mine = (ctrl = new AbortController());
			try {
				const vehicles = await api.lineVehicles(line.id, operator, mine.signal);
				current.buses.clearLayers();
				for (const v of vehicles) {
					current.L.marker([v.lat, v.lng], { icon: busIcon(current.L, v), title: `Ônibus ${v.prefix}` }).bindPopup(popup(v)).addTo(current.buses);
				}
				status = { at: new Date(), count: vehicles.length };
				failed = false;
			} catch {
				if (!mine.signal.aborted) failed = true;
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

<div class="space-y-2">
	<ul class="flex flex-wrap gap-x-4 gap-y-1 px-1 text-sm" aria-label="Legenda">
		{#each line.directions as d (d.direction)}
			<li class="flex min-w-0 items-center gap-1.5">
				<span class="h-1.5 w-5 shrink-0 rounded-full" style:background={COLORS[d.direction]} aria-hidden="true"></span>
				<span class="min-w-0"><span class="font-semibold">{d.direction === 'ida' ? 'Ida' : 'Volta'}:</span> <span class="text-soft">{d.name}</span></span>
			</li>
		{/each}
	</ul>
	<div bind:this={mapEl} role="region" aria-label="Mapa da linha {lineLabel(line.label)}" class="h-[55dvh] min-h-[280px] w-full overflow-hidden rounded-xl border border-rule bg-quiet shadow-card"></div>
	<p class="px-1 text-sm text-soft" role="status">
		{#if failed}
			Não conseguimos atualizar os ônibus agora. Tentamos de novo em instantes.{#if status} Última leitura às {clock(status.at)}.{/if}
		{:else if status}
			Atualizado às {clock(status.at)} · {status.count === 0 ? 'nenhum ônibus rastreado agora' : status.count === 1 ? '1 ônibus' : `${status.count} ônibus`}
		{:else}
			Procurando os ônibus…
		{/if}
	</p>
</div>
