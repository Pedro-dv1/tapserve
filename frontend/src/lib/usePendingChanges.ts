import { useCallback, useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { formSnapshot, savePendingForms } from './formChanges';

export function usePendingChanges(root: RefObject<HTMLDialogElement | null>, enabled: boolean, busy: boolean, close: () => void) {
  const baselines = useRef(new Map<HTMLFormElement, string>());
  const pending = useRef<(() => void) | null>(null);
  const bypass = useRef(false);
  const saving = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [visible, setVisible] = useState(false);
  const [savingBeforeLeave, setSavingBeforeLeave] = useState(false);
  const latest = useRef({ busy, close }); latest.current = { busy, close };
  const changedForms = useCallback(() => [...baselines.current].filter(([form, baseline]) => form.isConnected && formSnapshot(form) !== baseline).map(([form]) => form), []);
  const check = useCallback(() => setDirty(changedForms().length > 0), [changedForms]);
  const requestLeave = useCallback((action?: () => void) => {
    if (latest.current.busy || saving.current) return;
    if (enabled && changedForms().length) { pending.current = action ?? latest.current.close; setVisible(true); }
    else (action ?? latest.current.close)();
  }, [enabled, changedForms]);
  useEffect(() => {
    const node = root.current;
    if (!node) return;
    if (!enabled) {
      const leave = (event: Event) => { event.stopPropagation(); if (!latest.current.busy) ((event as CustomEvent<(() => void) | undefined>).detail ?? latest.current.close)(); };
      node.addEventListener('editor:leave', leave);
      return () => node.removeEventListener('editor:leave', leave);
    }
    const baselinesMap = baselines.current;
    function scan() {
      for (const form of node!.querySelectorAll<HTMLFormElement>('form:not([data-dirty-ignore])')) {
        if (form.closest('dialog') !== node) continue;
        if (!baselinesMap.has(form)) baselinesMap.set(form, formSnapshot(form, true));
      }
      for (const form of baselinesMap.keys()) if (!node!.contains(form)) baselinesMap.delete(form);
      check();
    }
    const changed = () => queueMicrotask(scan);
    const leave = (event: Event) => { event.stopPropagation(); requestLeave((event as CustomEvent<(() => void) | undefined>).detail); };
    const saved = (event: Event) => {
      if ((event as CustomEvent<boolean>).detail && event.target instanceof HTMLFormElement) baselinesMap.set(event.target, formSnapshot(event.target));
      check();
    };
    // Same-origin links use our contextual confirmation; browser exits keep beforeunload.
    const navigate = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || !(event.target instanceof Element)) return;
      const link = event.target.closest<HTMLAnchorElement>('a[href]');
      if (!link || link.target && link.target !== '_self' || link.hasAttribute('download')) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== location.origin || url.pathname === location.pathname && url.search === location.search) return;
      if (!changedForms().length) return;
      event.preventDefault(); event.stopPropagation();
      requestLeave(() => { bypass.current = true; window.location.assign(url.href); });
    };
    scan();
    const observer = new MutationObserver(scan);
    observer.observe(node, { childList: true, subtree: true, attributes: true, attributeFilter: ['value', 'checked', 'selected', 'data-loading'] });
    node.addEventListener('input', changed); node.addEventListener('change', changed); node.addEventListener('click', changed);
    node.addEventListener('editor:leave', leave); node.addEventListener('editor:save-result', saved);
    document.addEventListener('click', navigate, true);
    return () => { observer.disconnect(); baselinesMap.clear(); node.removeEventListener('input', changed); node.removeEventListener('change', changed); node.removeEventListener('click', changed); node.removeEventListener('editor:leave', leave); node.removeEventListener('editor:save-result', saved); document.removeEventListener('click', navigate, true); };
  }, [root, enabled, check, requestLeave, changedForms]);
  useEffect(() => {
    if (!enabled || !dirty) return;
    const unload = (event: BeforeUnloadEvent) => { if (!bypass.current && changedForms().length) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => window.removeEventListener('beforeunload', unload);
  }, [dirty, enabled, changedForms]);
  function continueEditing() { if (saving.current) return; pending.current = null; setVisible(false); }
  function discard() { if (saving.current || latest.current.busy) return; const action = pending.current; pending.current = null; bypass.current = true; setVisible(false); action?.(); }
  async function saveAndLeave() {
    if (saving.current || latest.current.busy) return;
    const forms = changedForms();
    saving.current = true; setSavingBeforeLeave(true);
    try {
      if (!await savePendingForms(forms)) return;
      const action = pending.current; pending.current = null; bypass.current = true; setVisible(false); action?.();
    } finally { saving.current = false; setSavingBeforeLeave(false); }
  }
  return { dirty, visible, savingBeforeLeave, requestLeave, continueEditing, discard, saveAndLeave };
}
