import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Icon } from './Interface';

const SuccessContext = createContext<((message: string) => void) | null>(null);
export function useSuccessToast() { return useContext(SuccessContext); }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [notice, setNotice] = useState<{ message: string } | null>(null);
  const popover = useRef<HTMLDivElement>(null);
  const notify = useCallback((message: string) => setNotice({ message }), []);
  useEffect(() => {
    if (!notice) return;
    popover.current?.showPopover?.();
    const timer = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);
  return <SuccessContext value={notify}>{children}{notice && <div ref={popover} popover="manual" className="ui-toast" role="status" aria-live="polite"><Icon name="check" /><span>{notice.message}</span><button type="button" className="icon-button" aria-label="Fechar notificação" onClick={() => setNotice(null)}><Icon name="close" /></button></div>}</SuccessContext>;
}

export default function Toast({ message, clear }: { message: string; clear: (value: string) => void }) {
  const notify = useContext(SuccessContext);
  useEffect(() => {
    if (message && notify) { notify(message); clear(''); }
  }, [message, notify, clear]);
  return null;
}
