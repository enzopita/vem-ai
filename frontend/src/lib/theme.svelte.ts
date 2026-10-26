export type ThemeChoice = 'system' | 'light' | 'dark';

const KEY = 'vemai:tema';
const ORDER: ThemeChoice[] = ['system', 'light', 'dark'];
const BAR = { light: '#ffffff', dark: '#151922' };
const systemDark = window.matchMedia('(prefers-color-scheme: dark)');

function stored(): ThemeChoice {
	try {
		const value = localStorage.getItem(KEY);
		return value === 'light' || value === 'dark' ? value : 'system';
	} catch {
		return 'system';
	}
}

export const theme = $state<{ choice: ThemeChoice }>({ choice: stored() });

function apply() {
	const dark = theme.choice === 'dark' || (theme.choice === 'system' && systemDark.matches);
	document.documentElement.dataset.theme = dark ? 'dark' : 'light';
	// Com escolha manual, a barra do navegador acompanha o tema do app, não o do sistema.
	for (const meta of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) meta.content = BAR[dark ? 'dark' : 'light'];
}

systemDark.addEventListener('change', () => theme.choice === 'system' && apply());
apply();

export function cycleTheme() {
	theme.choice = ORDER[(ORDER.indexOf(theme.choice) + 1) % ORDER.length];
	try {
		if (theme.choice === 'system') localStorage.removeItem(KEY);
		else localStorage.setItem(KEY, theme.choice);
	} catch {
		// sem armazenamento a escolha vale até fechar a aba
	}
	apply();
}
