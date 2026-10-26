import { version } from '$app/env';
import { assets, immutable } from '$app/manifest';
import { self as sw } from '$app/service-worker';

const CACHE = `vemai-${version}`;
const SHELL = '/';

sw.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(CACHE)
			.then((cache) => cache.addAll([SHELL, ...immutable.map((f) => f.path), ...assets.map((f) => f.path)]))
			.then(() => sw.skipWaiting())
	);
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
			.then(() => sw.clients.claim())
	);
});

// Os ativos têm hash no nome, então o cache vence. Navegações vão à rede e caem no shell da SPA offline. A API nunca é cacheada.
sw.addEventListener('fetch', (event) => {
	const { request } = event;
	const url = new URL(request.url);
	if (request.method !== 'GET' || url.origin !== sw.location.origin || url.pathname.startsWith('/api/')) return;

	if (request.mode === 'navigate') {
		event.respondWith(fetch(request).catch(async () => (await caches.match(SHELL)) ?? Response.error()));
		return;
	}
	event.respondWith(caches.match(request).then((hit) => hit ?? fetch(request)));
});

interface PushPayload {
	title: string;
	body: string;
	url: string;
}

function parsePayload(event: PushEvent): PushPayload {
	const raw: unknown = event.data?.json();
	const data = typeof raw === 'object' && raw !== null ? (raw as Partial<PushPayload>) : {};
	return { title: data.title ?? 'Vem Aí', body: data.body ?? '', url: data.url ?? '/' };
}

sw.addEventListener('push', (event) => {
	const { title, body, url } = parsePayload(event);
	event.waitUntil(
		sw.registration.showNotification(title, {
			body,
			icon: '/icon-192.png',
			badge: '/icon-192.png',
			data: { url }
		})
	);
});

sw.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const url: string = event.notification.data?.url ?? '/';
	event.waitUntil(
		sw.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
			const open = windows.find((w) => new URL(w.url).origin === sw.location.origin);
			if (!open) return sw.clients.openWindow(url);
			// navigate() falha em janelas que o SW não controla (e devolve null fora da origem); aí só resta focar a que existe.
			return open.navigate(url).then(
				(client) => (client ?? open).focus(),
				() => open.focus()
			);
		})
	);
});
