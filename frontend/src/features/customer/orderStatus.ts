export const statusNames = { NEW: 'Recebido', ACCEPTED: 'Aceito', PREPARING: 'Em preparo', READY: 'Pronto', DELIVERING: 'Em entrega', DELIVERED: 'Entregue', CANCELLED: 'Cancelado', REJECTED: 'Recusado' } as const;
export type OrderStatus = keyof typeof statusNames;
export const publicSteps = ['Recebido', 'Em preparo', 'Pronto', 'Entregue'];
export function statusStage(status: OrderStatus): number {
  return { NEW: 0, ACCEPTED: 0, PREPARING: 1, READY: 2, DELIVERING: 2, DELIVERED: 3, CANCELLED: -1, REJECTED: -1 }[status];
}
export function batchStatus(items: { status: OrderStatus }[]): OrderStatus {
  const relevant = items.filter(item => !['CANCELLED', 'REJECTED'].includes(item.status));
  if (relevant.length === 0) return items.some(item => item.status === 'REJECTED') ? 'REJECTED' : 'CANCELLED';
  const states = Object.keys(statusNames);
  return relevant.reduce((earliest, item) => states.indexOf(item.status) < states.indexOf(earliest) ? item.status : earliest, relevant[0]?.status ?? 'NEW');
}
export function isActiveBatch(items: { status: OrderStatus }[]): boolean {
  return items.some(item => !['DELIVERED', 'CANCELLED', 'REJECTED'].includes(item.status));
}
