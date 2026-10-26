export type ToastKind = 'ok' | 'error' | 'info';

export interface ToastAction {
	label: string;
	run: () => void;
}

export interface ToastMessage {
	id: number;
	kind: ToastKind;
	text: string;
	action?: ToastAction;
}

export const toasts = $state<ToastMessage[]>([]);

let nextId = 0;

export function notify(kind: ToastKind, text: string, action?: ToastAction) {
	const id = nextId++;
	toasts.push({ id, kind, text, action });
	// Com uma ação (desfazer) o aviso fica mais tempo, para dar tempo de alcançar o botão.
	setTimeout(() => dismiss(id), action ? 7000 : 4500);
}

export function dismiss(id: number) {
	const i = toasts.findIndex((t) => t.id === id);
	if (i >= 0) toasts.splice(i, 1);
}
