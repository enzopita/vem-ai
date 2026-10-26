// Chrome e Edge (Android e computador) avisam que o app pode ser instalado com este evento; Safari e Firefox não.
interface InstallPromptEvent extends Event {
	prompt(): Promise<void>;
	userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

// 'prompt': o navegador liberou a instalação nativa. 'ios' e 'manual': não há API, então a faixa ensina o caminho.
export type InstallOffer = 'none' | 'prompt' | 'ios' | 'manual';

const DISMISS_KEY = 'vemai:instalar-dispensado';
const DISMISS_DAYS = 7;

let deferred: InstallPromptEvent | null = null;

const standalone = () =>
	window.matchMedia('(display-mode: standalone)').matches ||
	(navigator as Navigator & { standalone?: boolean }).standalone === true;

// O iPad se apresenta como Mac; a tela de toque é o que o denuncia.
const ios = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (/macintosh/i.test(navigator.userAgent) && navigator.maxTouchPoints > 1);

function dismissedRecently(): boolean {
	try {
		const at = Number(localStorage.getItem(DISMISS_KEY));
		return at > 0 && Date.now() - at < DISMISS_DAYS * 86_400_000;
	} catch {
		return false;
	}
}

// O Chrome só dispara beforeinstallprompt depois de algum uso da página, então a faixa já abre com o caminho manual
// e troca para o botão "Instalar" quando o evento chegar.
export const install = $state<{ offer: InstallOffer }>({
	offer: standalone() || dismissedRecently() ? 'none' : ios() ? 'ios' : 'manual'
});

// O evento pode chegar antes de qualquer componente montar, então o ouvinte nasce junto com o módulo.
window.addEventListener('beforeinstallprompt', (event) => {
	event.preventDefault();
	deferred = event as InstallPromptEvent;
	if (!dismissedRecently()) install.offer = 'prompt';
});

window.addEventListener('appinstalled', () => {
	deferred = null;
	install.offer = 'none';
});

export async function promptInstall() {
	if (!deferred) return;
	await deferred.prompt();
	const { outcome } = await deferred.userChoice;
	deferred = null;
	install.offer = 'none';
	if (outcome === 'dismissed') dismissInstall();
}

export function dismissInstall() {
	install.offer = 'none';
	try {
		localStorage.setItem(DISMISS_KEY, String(Date.now()));
	} catch {
		// sem armazenamento a faixa só volta na próxima visita
	}
}
