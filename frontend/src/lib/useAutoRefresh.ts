import { useEffect, useRef } from 'react';

// Slow fallback complements domain events and resumes immediately after focus/reconnection.
export function useAutoRefresh(refresh: () => void, enabled = true) {
  const latest = useRef(refresh); latest.current = refresh;
  useEffect(() => {
    if (!enabled) return;
    const update = () => { if (navigator.onLine && document.visibilityState !== 'hidden' && !document.querySelector('dialog[data-dirty="true"]')) latest.current(); };
    const timer = window.setInterval(update, 30_000);
    window.addEventListener('focus', update); window.addEventListener('online', update); document.addEventListener('visibilitychange', update);
    return () => { window.clearInterval(timer); window.removeEventListener('focus', update); window.removeEventListener('online', update); document.removeEventListener('visibilitychange', update); };
  }, [enabled]);
}
