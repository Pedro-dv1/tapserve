export type FulfillmentMode = 'DINE_IN' | 'TAKEAWAY';
export function fulfillmentMode(value: unknown): FulfillmentMode {
  if (value === undefined) return 'DINE_IN';
  if (value === 'DINE_IN' || value === 'TAKEAWAY') return value;
  throw new Error('Modalidade de consumo inválida.');
}
