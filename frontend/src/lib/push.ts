import { api, type PushKeys } from './api';

export type PushSupport = 'supported' | 'needs-home-screen' | 'unsupported';

export class PermissionDeniedError extends Error {
	constructor() {
		super('Sem permissão de notificação não é possível avisar você. Libere nas configurações do navegador.');
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
	return capable ? 'supported' : 'unsupported';
}

export const permissionDenied = () => 'Notification' in window && Notification.permission === 'denied';

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
