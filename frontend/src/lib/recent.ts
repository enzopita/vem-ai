import type { Stop } from './api';

const KEY = 'vemai:pontos-recentes';
const MAX = 4;

/** Os pontos abertos por último, do mais recente ao mais antigo. Vazio quando o navegador não guarda nada. */
export function recentStops(): Stop[] {
	try {
		const raw: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
		return Array.isArray(raw)
			? raw.filter((s): s is Stop => typeof s?.id === 'string' && typeof s?.name === 'string')
			: [];
	} catch {
		return [];
	}
}

export function rememberStop(stop: Stop) {
	try {
		const rest = recentStops().filter((s) => s.id !== stop.id);
		localStorage.setItem(KEY, JSON.stringify([stop, ...rest].slice(0, MAX)));
	} catch {
		// sem armazenamento (aba privada, cota): o app funciona igual, só não lembra o ponto
	}
}

export function forgetStop(id: string) {
	try {
		localStorage.setItem(KEY, JSON.stringify(recentStops().filter((s) => s.id !== id)));
	} catch {
		// idem
	}
}

export const stopHref = (stop: Stop) => `/ponto/${encodeURIComponent(stop.id)}?nome=${encodeURIComponent(stop.name)}`;
