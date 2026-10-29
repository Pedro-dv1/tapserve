import { Icon } from './Interface';
import type { FulfillmentMode } from '../features/customer/fulfillment';

export function FulfillmentBadge({ mode, showDineIn = false }: { mode: FulfillmentMode | undefined; showDineIn?: boolean }) {
  if (mode !== 'TAKEAWAY' && !showDineIn) return null;
  return <span className={`fulfillment-badge ${mode === 'TAKEAWAY' ? 'takeaway' : ''}`}><Icon name={mode === 'TAKEAWAY' ? 'bag' : 'table'} size={16} />{mode === 'TAKEAWAY' ? 'Para levar' : 'Mesa'}</span>;
}
export function FulfillmentSelector({ value, change, disabled = false }: { value: FulfillmentMode; change: (value: FulfillmentMode) => void; disabled?: boolean }) {
  return <fieldset className="fulfillment-selector" disabled={disabled}><legend>Como vai consumir?</legend><div className="segmented-control">{(['DINE_IN', 'TAKEAWAY'] as const).map(mode => <button type="button" key={mode} aria-pressed={value === mode} className={value === mode ? 'selected' : ''} onClick={() => change(mode)}><Icon name={mode === 'TAKEAWAY' ? 'bag' : 'table'} size={18} />{mode === 'TAKEAWAY' ? 'Para levar' : 'Consumir aqui'}</button>)}</div></fieldset>;
}
