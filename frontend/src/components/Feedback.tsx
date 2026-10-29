import type { ReactNode } from 'react';
import { Icon } from './Interface';

export default function Feedback({ tone = 'info', children }: { tone?: 'info' | 'success' | 'warning' | 'processing' | 'error'; children: ReactNode }) {
  return <div className={`ui-feedback feedback-${tone}`} role={tone === 'error' ? 'alert' : 'status'}><Icon name={tone === 'success' ? 'check' : tone === 'processing' ? 'clock' : 'info'} size={18} /><p>{children}</p></div>;
}
