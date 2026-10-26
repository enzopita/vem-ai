const KEY = 'vemai:operator';

export function loadLastOperator(): string | null {
	try {
		return localStorage.getItem(KEY);
	} catch {
		return null;
	}
}

export function saveLastOperator(name: string) {
	try {
		localStorage.setItem(KEY, name);
	} catch {
		// armazenamento bloqueado: só deixamos de lembrar a escolha
	}
}
