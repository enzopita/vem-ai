export interface Coord {
	lat: number;
	lng: number;
}

const EARTH_RADIUS_M = 6_371_000;
const rad = (deg: number) => (deg * Math.PI) / 180;

/** Distância em linha reta (haversine) entre dois pontos, em metros. */
export function distanceM(a: Coord, b: Coord): number {
	const dLat = rad(b.lat - a.lat);
	const dLng = rad(b.lng - a.lng);
	const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
	return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

/** Os `n` itens mais perto de `here`, do mais perto ao mais longe. */
export function nearest<T extends Coord>(items: T[], here: Coord, n: number): (T & { distance: number })[] {
	return items
		.map((item) => ({ ...item, distance: distanceM(item, here) }))
		.sort((a, b) => a.distance - b.distance)
		.slice(0, n);
}

const km = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function formatDistance(m: number): string {
	if (m < 1000) return `${Math.max(10, Math.round(m / 10) * 10)} m`;
	return `${km.format(m / 1000)} km`;
}
