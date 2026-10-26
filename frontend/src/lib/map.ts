import type L from 'leaflet';
import type { Direction } from './api';

// Laranja e roxo se distinguem do azul dos pontos e do verde/azul das placas, e entre si para daltônicos.
export const DIRECTION_COLORS: Record<Direction, string> = { ida: '#c2410c', volta: '#6d28d9' };

export interface BaseMap {
	L: typeof L;
	map: L.Map;
	accent: string;
}

/** Leaflet pesa, então só carrega quando um mapa é aberto. */
export async function createMap(el: HTMLElement, options: L.MapOptions): Promise<BaseMap> {
	const [{ default: leaflet }] = await Promise.all([import('leaflet'), import('leaflet/dist/leaflet.css')]);
	const accent = getComputedStyle(el).getPropertyValue('--accent').trim() || '#0a5fc4';
	const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
	const map = leaflet.map(el, { zoomAnimation: !calm, fadeAnimation: !calm, markerZoomAnimation: !calm, ...options });
	leaflet.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map);
	return { L: leaflet, map, accent };
}

/** Marcador de ponto, igual em todos os mapas. */
export const stopMarker = (leaflet: typeof L, at: L.LatLngExpression, accent: string) =>
	leaflet.circleMarker(at, { radius: 7, weight: 3, color: accent, fillColor: '#ffffff', fillOpacity: 1 });
