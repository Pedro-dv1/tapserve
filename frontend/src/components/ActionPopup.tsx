import Modal from './Modal';
import Feedback from './Feedback';
import { Button } from './Interface';
import { useEffect, useRef } from 'react';

export type ActionNotice = { title: string; message: string; tone?: 'success' | 'warning' | 'info' };
export default function ActionPopup({ notice, close }: { notice: ActionNotice | null; close: () => void }) {
  const dismiss = useRef(close);
  useEffect(() => { dismiss.current = close; }, [close]);
  useEffect(() => {
    if (!notice || notice.tone && notice.tone !== 'success') return;
    const timer = window.setTimeout(() => dismiss.current(), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);
  if (!notice) return null;
  return <Modal open title={notice.title} close={close}><Feedback tone={notice.tone ?? 'success'}>{notice.message}</Feedback><div className="dialog-actions"><Button onClick={close}>Entendido</Button></div></Modal>;
}
