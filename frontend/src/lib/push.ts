import { api, type PushKeys } from './api';

export type PushSupport = 'supported' | 'denied' | 'needs-home-screen' | 'unsupported';

export class PermissionDeniedError extends Error {
	constructor() {
		super('Sem a permissão de notificação não dá para avisar você. Toque em "Ativar alerta" de novo para permitir.');
		this.name = 'PermissionDeniedError';
	}
}

export interface PushIdentity {
	endpoint: string;
	keys: PushKeys;
}

export function pushSupport(): PushSupport {
	const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
	const standalone =
		window.matchMedia('(display-mode: standalone)').matches ||
		(navigator as Navigator & { standalone?: boolean }).standalone === true;
	if (ios && !standalone) return 'needs-home-screen';
	const capable = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
	if (!capable) return 'unsupported';
	return Notification.permission === 'denied' ? 'denied' : 'supported';
}

/** O navegador ainda vai perguntar: a pessoa precisa saber antes por que o pedido aparece. */
export const willAskPermission = () => 'Notification' in window && Notification.permission === 'default';

function urlBase64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
	const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
	const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
	return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

export async function currentSubscription(): Promise<PushSubscription | null> {
	const reg = await navigator.serviceWorker.ready;
	return reg.pushManager.getSubscription();
}

export async function subscribe(): Promise<PushIdentity> {
	if ((await Notification.requestPermission()) !== 'granted') throw new PermissionDeniedError();
	const reg = await navigator.serviceWorker.ready;
	const existing = await reg.pushManager.getSubscription();
	const sub =
		existing ??
		(await reg.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: urlBase64ToBytes((await api.vapidKey()).key)
		}));
	return identify(sub);
}

function identify(sub: PushSubscription): PushIdentity {
	const { endpoint, keys } = sub.toJSON();
	if (!endpoint || !keys?.p256dh || !keys.auth) throw new Error('O navegador devolveu uma inscrição incompleta.');
	return { endpoint, keys: { p256dh: keys.p256dh, auth: keys.auth } };
}
