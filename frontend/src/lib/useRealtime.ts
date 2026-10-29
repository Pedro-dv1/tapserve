import { useCallback, useSyncExternalStore } from 'react';
import { realtimeSnapshot, subscribeRealtime } from './realtime';

export function useRealtime(kind: 'public' | 'staff') {
  const subscribe = useCallback((listener: () => void) => subscribeRealtime(kind, listener), [kind]);
  const snapshot = useCallback(() => realtimeSnapshot(kind), [kind]);
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}
