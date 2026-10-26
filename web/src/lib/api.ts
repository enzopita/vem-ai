export interface Stop {
	id: string;
	name: string;
}

export interface Line {
	id: string;
	label: string;
}

export interface Prediction {
	line: Line;
	vehicle: string;
	eta_min: number;
}

export interface StopBoard {
	stop_id: string;
	predictions: Prediction[];
	other_lines: Line[];
}

export interface PushKeys {
	p256dh: string;
	auth: string;
}

export interface SubscriptionIn {
	endpoint: string;
	keys: PushKeys;
	operator: string;
	stop_id: string;
	stop_name: string;
	line_id: string;
	line_label: string;
	time: string;
	lead_min: number;
}

export interface Subscription extends SubscriptionIn {
	id: number;
}

export interface Operator {
	name: string;
	online: boolean;
}

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status: number
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	let resp: Response;
	try {
		resp = await fetch(path, init);
	} catch (cause) {
		if (cause instanceof DOMException && cause.name === 'AbortError') throw cause;
		throw new ApiError('Sem conexão com o servidor. Verifique sua internet.', 0);
	}
	if (!resp.ok) {
		const body: unknown = await resp.json().catch(() => null);
		const detail = typeof body === 'object' && body !== null && 'detail' in body ? body.detail : null;
		throw new ApiError(typeof detail === 'string' ? detail : 'Erro inesperado.', resp.status);
	}
	return resp.status === 204 ? (undefined as T) : ((await resp.json()) as T);
}

const stopPath = (operator: string, stopId: string) =>
	`/api/operators/${encodeURIComponent(operator)}/stops/${encodeURIComponent(stopId)}`;

const ownedPath = (sub: Subscription, suffix = '') =>
	`/api/subscriptions/${sub.id}${suffix}?endpoint=${encodeURIComponent(sub.endpoint)}`;

export const messageOf = (err: unknown) => (err instanceof Error ? err.message : 'Erro inesperado.');

export const api = {
	operators: () => request<Operator[]>('/api/operators'),
	searchStops: (operator: string, q: string, signal?: AbortSignal) =>
		request<Stop[]>(`/api/operators/${encodeURIComponent(operator)}/stops?q=${encodeURIComponent(q)}`, {
			signal
		}),
	board: (operator: string, stopId: string, signal?: AbortSignal) =>
		request<StopBoard>(`${stopPath(operator, stopId)}/board`, { signal }),
	vapidKey: () => request<{ key: string }>('/api/vapid-public-key'),
	createSubscription: (body: SubscriptionIn) =>
		request<Subscription>('/api/subscriptions', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		}),
	listSubscriptions: (endpoint: string) =>
		request<Subscription[]>(`/api/subscriptions?endpoint=${encodeURIComponent(endpoint)}`),
	deleteSubscription: (sub: Subscription) => request<void>(ownedPath(sub), { method: 'DELETE' }),
	testSubscription: (sub: Subscription) => request<void>(ownedPath(sub, '/test'), { method: 'POST' })
};
