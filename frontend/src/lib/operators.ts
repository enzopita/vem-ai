const LABELS: Record<string, string> = { piracicabana: 'Piracicabana', brmobilidadebs: 'BR Mobilidade' };

export const operatorLabel = (key: string) => LABELS[key] ?? key;

export function unavailableNotice(unavailable: string[]): string {
	if (unavailable.length === 0) return '';
	const down = unavailable.map(operatorLabel).join(' e ');
	const up = Object.keys(LABELS)
		.filter((key) => !unavailable.includes(key))
		.map(operatorLabel)
		.join(' e ');
	return up ? `${down} fora do ar: mostrando só as linhas da ${up}.` : `${down} fora do ar.`;
}
