import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const config = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...Object.fromEntries(Object.entries(process.env).filter(([key]) => key.startsWith('VITE_'))) };
  const backend = config.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  const target = new URL(backend);
  if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.pathname !== '/' || target.search || target.hash) throw new Error('VITE_BACKEND_URL must be an HTTP(S) origin without credentials.');
  const profile = config.VITE_TAPSERVE_ENV;
  const port = Number(config.VITE_FRONTEND_PORT || 5173);
  if (profile && (!['dev', 'qa'].includes(profile) || mode !== (profile === 'dev' ? 'development' : 'qa') || backend !== `http://127.0.0.1:${profile === 'dev' ? 8004 : 8003}` || port !== (profile === 'dev' ? 5177 : 5176))) throw new Error('Local frontend mode, API and ports must belong to the same environment.');
  return {
  server: {
    host: profile ? '127.0.0.1' : '0.0.0.0',
    port,
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
