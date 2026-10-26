import { api, type StopCatalog } from './api';

let cached: Promise<StopCatalog> | undefined;

/** Uma só carga do catálogo de pontos por visita: quem pede depois reaproveita a resposta. */
export function loadCatalog(): Promise<StopCatalog> {
	cached ??= api
		.catalog()
		.then((found) => {
			// Catálogo ainda sendo montado no servidor: o próximo pedido tenta de novo.
			if (found.stops.length === 0) cached = undefined;
			return found;
		})
		.catch((err) => {
			cached = undefined;
			throw err;
		});
	return cached;
}
