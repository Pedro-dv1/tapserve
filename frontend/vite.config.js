import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const backend = process.env.VITE_BACKEND_URL || loadEnv(mode, process.cwd(), 'VITE_').VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  const target = new URL(backend);
  if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.pathname !== '/' || target.search || target.hash) throw new Error('VITE_BACKEND_URL must be an HTTP(S) origin without credentials.');
  return {
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/ws': { target: backend, ws: true, changeOrigin: true, rewriteWsOrigin: false },
    },
    headers: {
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
    },
  },
  build: { sourcemap: false },
};
});
