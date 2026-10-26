const LABELS: Record<string, string> = { piracicabana: 'Piracicabana', brmobilidadebs: 'BR Mobilidade' };

export const operatorLabel = (key: string) => LABELS[key] ?? key;

export type LineKind = 'municipal' | 'intermunicipal';

// Na Baixada a Piracicabana atende as linhas municipais e a BR Mobilidade as intermunicipais.
const KINDS: Record<string, LineKind> = { piracicabana: 'municipal', brmobilidadebs: 'intermunicipal' };

/** Tipo da linha pela operadora; indefinido para alertas antigos, criados antes de a operadora ser guardada. */
export const lineKind = (operator?: string): LineKind | undefined => (operator ? KINDS[operator] : undefined);

/** Complemento para leitores de tela: a cor da placa não pode ser o único jeito de saber o tipo. */
export const kindSuffix = (operator?: string) => {
	const kind = lineKind(operator);
	return kind ? `, ${kind}` : '';
};

export function unavailableNotice(unavailable: string[]): string {
	if (unavailable.length === 0) return '';
	const down = unavailable.map(operatorLabel).join(' e ');
	const up = Object.keys(LABELS)
		.filter((key) => !unavailable.includes(key))
		.map(operatorLabel)
		.join(' e ');
	return up ? `${down} fora do ar: mostrando só as linhas da ${up}.` : `${down} fora do ar.`;
}
