export type ToastKind = 'ok' | 'error' | 'info';

export interface ToastMessage {
	id: number;
	kind: ToastKind;
	text: string;
}

export const toasts = $state<ToastMessage[]>([]);

let nextId = 0;

export function notify(kind: ToastKind, text: string, ms = 4500) {
	const id = nextId++;
	toasts.push({ id, kind, text });
	setTimeout(() => dismiss(id), ms);
}

export function dismiss(id: number) {
	const i = toasts.findIndex((t) => t.id === id);
	if (i >= 0) toasts.splice(i, 1);
}
