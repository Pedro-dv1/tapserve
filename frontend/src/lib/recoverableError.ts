// shortcut: React 19.3 misses Chrome's viewport cancellation suffix; remove after its classifier is upgraded.
export function reportRecoverableError(error: unknown) {
  if (error instanceof DOMException && error.name === 'InvalidStateError' && error.message === 'Transition was aborted because of invalid state. Viewport size changed') return;
  reportError(error);
}
