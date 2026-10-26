import type { Line, RegionBoard } from './api';

export interface Arrival {
	/** Minutos até o veículo; 0 é "chegando". */
	eta: number;
	vehicle: string;
	/** Vazio quando a operadora não informa o motorista. */
	driver: string;
}

export interface LineGroup {
	line: Line;
	/** Um item por veículo da linha, do mais próximo ao mais longe. */
	arrivals: Arrival[];
}

/** Uma entrada por linha, ordenadas pelo ônibus mais próximo de cada uma. */
export function groupByLine(board: RegionBoard): LineGroup[] {
	const byId = new Map<string, LineGroup>();
	for (const p of board.predictions) {
		const group = byId.get(p.line.id) ?? { line: p.line, arrivals: [] };
		group.arrivals.push({ eta: p.eta_min, vehicle: p.vehicle, driver: p.driver });
		byId.set(p.line.id, group);
	}
	const groups = [...byId.values()];
	for (const g of groups) g.arrivals.sort((a, b) => a.eta - b.eta);
	return groups.sort((a, b) => a.arrivals[0].eta - b.arrivals[0].eta);
}

/**
 * Linhas com um veículo "chegando" na leitura anterior que não aparece na atual: o app não sabe se ele
 * passou ou se o GPS caiu, então mostra as duas hipóteses. Com uma operadora fora do ar os veículos
 * dela somem do quadro, e compará-los daria todos por perdidos.
 */
export function vanishedArrivals(prev: RegionBoard | null, next: RegionBoard): Line[] {
	if (!prev || prev.unavailable.length > 0 || next.unavailable.length > 0) return [];
	const present = new Set(next.predictions.map((p) => `${p.line.id}|${p.vehicle}`));
	const lines = new Map<string, Line>();
	for (const p of prev.predictions) {
		if (p.eta_min === 0 && !present.has(`${p.line.id}|${p.vehicle}`)) lines.set(p.line.id, p.line);
	}
	return [...lines.values()];
}

/** Rampa fixa: quanto mais perto o ônibus, maior o número. */
export function etaScale(eta: number): string {
	if (eta <= 5) return 'text-[1.375rem]';
	if (eta <= 10) return 'text-xl';
	if (eta <= 15) return 'text-lg';
	return 'text-base';
}


export const clock = (d: Date) => d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

/** Algumas operadoras mandam "12:40:41", outras "26/10/2026 12:40:41"; a hora é o que importa. */
export const seenClock = (seenAt: string) => /\d{2}:\d{2}/.exec(seenAt)?.[0] ?? seenAt;
