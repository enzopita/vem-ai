const CONNECTORS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em', 'na', 'no']);
const ROMAN = /^(?=[IVXLCDM])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$/;
const WORD = /[\p{L}\p{N}.]+/gu;

const upper = (s: string) => s.toLocaleUpperCase('pt-BR');
const lower = (s: string) => s.toLocaleLowerCase('pt-BR');

/** O feed das operadoras manda o nome do ponto em caixa alta; isto só muda a exibição, nunca o valor guardado ou enviado. */
export function stopLabel(raw: string): string {
	let first = true;
	return raw.replace(WORD, (word, at: number) => {
		const isFirst = first;
		first = false;
		const dotted = word.endsWith('.');
		const core = dotted ? word.slice(0, -1) : word;
		const down = lower(core);
		// "Rua A" termina numa letra solta que é nome, não conector.
		const last = !/[\p{L}\p{N}]/u.test(raw.slice(at + word.length));
		if (!dotted && !isFirst && !last && CONNECTORS.has(down)) return down;
		if (!dotted && ROMAN.test(upper(core))) return upper(core);
		// Abreviação com ponto ("DR.", "PÇA.") é palavra encurtada, não sigla, mesmo sem vogal.
		if (!dotted && !/[aeiouáàâãéêíóôõúü]/.test(down)) return word.toLocaleUpperCase('pt-BR');
		return upper(down.charAt(0)) + down.slice(1) + (dotted ? '.' : '');
	});
}

/** Nome de pessoa em caixa alta no feed ("FREDERICO DA SILVA") vira "Frederico da Silva". */
export function personName(raw: string): string {
	return lower(raw.trim())
		.split(/\s+/)
		.map((w, i) => (i > 0 && CONNECTORS.has(w) ? w : upper(w.charAt(0)) + w.slice(1)))
		.join(' ');
}

/** A operadora escreve a mesma linha como "04" no quadro e "CIRCULAR 004" na lista; o app usa sempre a forma curta. */
export function lineLabel(raw: string): string {
	const circular = /^CIRCULAR\s+0*(\d+)$/i.exec(raw.trim());
	return circular ? circular[1].padStart(2, '0') : raw;
}
