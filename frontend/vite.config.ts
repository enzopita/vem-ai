import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit({ adapter: adapter({ fallback: 'index.html' }) })],
	// O Vite recusa nomes de host desconhecidos; .ts.net libera o acesso pelo tailnet (tailscale serve).
	server: { proxy: { '/api': 'http://localhost:8000' }, allowedHosts: ['.ts.net'] }
});
