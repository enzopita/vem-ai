import type { ScheduleDay, Trip } from './api';

const toMinutes = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));

/** A tabela segue a ordem do dia de operação: um "00:15" depois de "23:40" é da madrugada seguinte, não do começo do dia. */
export const operatingMinutes = (times: string[]) => {
	let offset = 0;
	let prev = -1;
	return times.map((t) => {
		const m = toMinutes(t) + offset;
		if (m < prev) offset += 1440;
		prev = toMinutes(t) + offset;
		return prev;
	});
};

export const dayOf = (d: Date): ScheduleDay => (d.getDay() === 0 ? 'domingos' : d.getDay() === 6 ? 'sabados' : 'uteis');

/** Índice da primeira saída que ainda não passou, ou -1 se não há mais nenhuma hoje. */
export function nextIndex(trips: Trip[], now: Date): number {
	const nowMin = now.getHours() * 60 + now.getMinutes();
	return operatingMinutes(trips.map((t) => t.departure)).findIndex((m) => m >= nowMin);
}
