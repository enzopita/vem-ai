export interface Stop {
	id: string;
	name: string;
}

export interface Line {
	id: string;
	label: string;
	/** Operadora que atende a linha; define se ela é municipal ou intermunicipal. */
	operator?: string;
	/** Itinerário resumido, quando a operadora informa (linhas a mais de 20 min). */
	description?: string;
}

export interface Prediction {
	line: Line;
	vehicle: string;
	driver: string;
	eta_min: number;
}

export type Direction = 'ida' | 'volta';
export type ScheduleDay = 'uteis' | 'sabados' | 'domingos';

export interface LatLng {
	lat: number;
	lng: number;
}

export interface LineDirection {
	direction: Direction;
	name: string;
	streets: string[];
	path: LatLng[];
}

export interface Trip {
	departure: string;
	arrival: string;
}

export interface DaySchedule {
	day: ScheduleDay;
	ida: Trip[];
	volta: Trip[];
}

export interface LineDetail extends Line {
	description: string;
	directions: LineDirection[];
	stops: (LatLng & { name: string })[];
	schedules: DaySchedule[];
}

export interface LiveVehicle extends LatLng {
	prefix: string;
	driver: string;
	direction: Direction;
	seen_at: string;
}

export interface StopBoard {
	stop_id: string;
	predictions: Prediction[];
	other_lines: Line[];
}

export interface RegionBoard extends StopBoard {
	unavailable: string[];
}

export interface LineSearch {
	lines: Line[];
	unavailable: string[];
}

export interface StopSearch {
	stops: Stop[];
	unavailable: string[];
}

export interface CatalogStop extends Stop {
	lat: number;
	lng: number;
}

export interface StopCatalog {
	stops: CatalogStop[];
	unavailable: string[];
}

export interface PushKeys {
	p256dh: string;
	auth: string;
}

export interface SubscriptionIn {
	endpoint: string;
	keys: PushKeys;
	stop_id: string;
	stop_name: string;
	line_id: string;
	line_label: string;
	line_operator: string;
	time: string;
	lead_min: number;
}

export interface Subscription extends SubscriptionIn {
	id: number;
}

export interface CollectorStatus {
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

const ownedPath = (sub: Subscription, suffix = '') =>
	`/api/subscriptions/${sub.id}${suffix}?endpoint=${encodeURIComponent(sub.endpoint)}`;

export const messageOf = (err: unknown) => (err instanceof Error ? err.message : 'Erro inesperado.');

export const api = {
	status: () => request<CollectorStatus[]>('/api/status'),
	searchStops: (q: string, signal?: AbortSignal) =>
		request<StopSearch>(`/api/stops?q=${encodeURIComponent(q)}`, { signal }),
	searchLines: (q: string, signal?: AbortSignal) =>
		request<LineSearch>(`/api/lines?q=${encodeURIComponent(q)}`, { signal }),
	catalog: (signal?: AbortSignal) => request<StopCatalog>('/api/stops/catalog', { signal }),
	board: (stopId: string, signal?: AbortSignal) =>
		request<RegionBoard>(`/api/stops/${encodeURIComponent(stopId)}/board`, { signal }),
	line: (id: string, operator: string, signal?: AbortSignal) =>
		request<LineDetail>(`/api/lines/${encodeURIComponent(id)}?operator=${encodeURIComponent(operator)}`, { signal }),
	lineVehicles: (id: string, operator: string, signal?: AbortSignal) =>
		request<LiveVehicle[]>(`/api/lines/${encodeURIComponent(id)}/vehicles?operator=${encodeURIComponent(operator)}`, { signal }),
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
