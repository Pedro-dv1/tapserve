// A closed popover can leave its trigger connected but impossible to focus.
export function restoreFocus(candidates: (HTMLElement | null)[]) {
  for (const target of candidates) {
    if (!target?.isConnected || target === target.ownerDocument.body || target === target.ownerDocument.documentElement || target.matches(':disabled') || target.closest('[inert]') || !target.getClientRects().length) continue;
    if (target.checkVisibility && !target.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const style = target.ownerDocument.defaultView?.getComputedStyle(target);
    if (style?.visibility === 'hidden' || style?.visibility === 'collapse' || style?.opacity === '0') continue;
    target.focus({ preventScroll: true });
    if (target.ownerDocument.activeElement === target) return;
  }
}
