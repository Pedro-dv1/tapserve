import { addTransitionType, startTransition } from 'react';

export function startMotionTransition(update: () => void, type?: 'navigation') {
  // CSS alone still schedules native snapshots when motion is disabled.
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) update();
  else startTransition(() => { if (type) addTransitionType(type); update(); });
}
