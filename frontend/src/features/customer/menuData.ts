import { record, text } from '../../lib/api.ts';
export type Product = { id: string; name: string; description: string; base_price: string; has_image: boolean; has_video: boolean; most_ordered: boolean; ordered_quantity: number; image_version: string };
export type Option = { id: string; name: string; additional_price: string };
export type Group = { id: string; name: string; selection_type: 'SINGLE' | 'MULTIPLE'; required: boolean; min_choices: number; max_choices: number; options: Option[] };
export type Photo = { id: string; alt_text: string; position: number };
export type ProductDetail = Product & { groups: Group[]; takeaway_enabled: boolean; long_description: string; ingredients: string; serving_info: string; allergen_info: string; photos: Photo[] };
export const NOTE_LIMIT = 500;
export function cents(value: string): number {
  if (!/^\d{1,10}\.\d{2}$/.test(value)) throw new Error('Valor monetário inválido.');
  const [whole, fraction] = value.split('.');
  const result = Number(whole) * 100 + Number(fraction);
  if (!Number.isSafeInteger(result)) throw new Error('Valor monetário excede o limite.');
  return result;
}
export function formatCents(value: number): string {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error('Valor monetário inválido.');
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value / 100);
}
export function brl(value: string): string { return formatCents(cents(value)); }
export function decodeProduct(data: unknown): Product {
  const row = record(data); const price = text(row.base_price); cents(price);
  if (typeof row.has_image !== 'boolean') throw new Error('Resposta inválida do serviço.');
  if (row.has_video !== undefined && typeof row.has_video !== 'boolean') throw new Error('Resposta inválida do serviço.');
  if (row.image_version !== undefined && (typeof row.image_version !== 'string' || !/^(?:[0-9a-f]{16})?$/.test(row.image_version))) throw new Error('Versão de imagem inválida.');
  if (row.most_ordered !== undefined && typeof row.most_ordered !== 'boolean') throw new Error('Resposta inválida do serviço.');
  if (row.ordered_quantity !== undefined && (typeof row.ordered_quantity !== 'number' || !Number.isSafeInteger(row.ordered_quantity) || row.ordered_quantity < 0)) throw new Error('Resposta inválida do serviço.');
  return { id: text(row.id), name: text(row.name), description: text(row.description), base_price: price, has_image: row.has_image, image_version: typeof row.image_version === 'string' ? row.image_version : '', has_video: row.has_video === true, most_ordered: row.most_ordered === true, ordered_quantity: typeof row.ordered_quantity === 'number' ? row.ordered_quantity : 0 };
}
export function decodeDetail(data: unknown): ProductDetail {
  const input = record(data);
  const raw = input.individual_options;
  if (raw !== undefined && !Array.isArray(raw)) throw new Error('Opções individuais inválidas.');
  const direct = (raw ?? []) as unknown[];
  if (direct.length) {
    if (!Array.isArray(input.groups)) throw new Error('Resposta inválida do serviço.');
    const grouped = input.groups.flatMap(value => { const group = record(value); return Array.isArray(group.options) ? group.options.map(value => text(record(value).id)) : []; });
    const options = direct.filter(value => !grouped.includes(text(record(value).id)));
    data = { ...input, groups: [...input.groups, ...(options.length ? [{ id: 'individual', name: 'Adicionais', selection_type: 'MULTIPLE', required: false, min_choices: 0, max_choices: options.length, options }] : [])] };
  }
  const row = record(data); if (!Array.isArray(row.groups)) throw new Error('Resposta inválida do serviço.');
  if (row.takeaway_enabled !== undefined && typeof row.takeaway_enabled !== 'boolean') throw new Error('Modalidade inválida.');
  if (row.photos !== undefined && (!Array.isArray(row.photos) || row.photos.length > 6)) throw new Error('Galeria inválida.');
  const photos = ((row.photos ?? []) as unknown[]).map(value => {
    const photo = record(value), id = text(photo.id);
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id) || typeof photo.position !== 'number' || !Number.isInteger(photo.position) || photo.position < 0) throw new Error('Galeria inválida.');
    return { id, alt_text: text(photo.alt_text), position: photo.position };
  });
  return { ...decodeProduct(data), long_description: row.long_description === undefined ? '' : text(row.long_description), ingredients: row.ingredients === undefined ? '' : text(row.ingredients), serving_info: row.serving_info === undefined ? '' : text(row.serving_info), allergen_info: row.allergen_info === undefined ? '' : text(row.allergen_info), photos, takeaway_enabled: row.takeaway_enabled === true, groups: row.groups.map((value: unknown) => {
    const group = record(value);
    if ((group.selection_type !== 'SINGLE' && group.selection_type !== 'MULTIPLE') || typeof group.required !== 'boolean' || typeof group.min_choices !== 'number' || typeof group.max_choices !== 'number' || !Number.isInteger(group.min_choices) || !Number.isInteger(group.max_choices) || group.min_choices < 0 || group.max_choices < group.min_choices || !Array.isArray(group.options)) throw new Error('Resposta inválida do serviço.');
    return { id: text(group.id), name: text(group.name), selection_type: group.selection_type, required: group.required, min_choices: group.min_choices, max_choices: group.max_choices, options: group.options.map((option: unknown) => { const choice = record(option); const price = text(choice.additional_price); cents(price); return { id: text(choice.id), name: text(choice.name), additional_price: price }; }) };
  }) };
}
export function selectionError(product: ProductDetail, selected: string[]): string {
  const options = product.groups.flatMap(group => group.options);
  if (new Set(selected).size !== selected.length || selected.some(id => !options.some(option => option.id === id))) return 'Uma opção não está mais disponível. Revise sua seleção.';
  for (const group of product.groups) {
    const count = group.options.filter(option => selected.includes(option.id)).length;
    if (count < group.min_choices || count > group.max_choices) return `Confira ${group.name}: escolha de ${group.min_choices} a ${group.max_choices} opções.`;
  }
  return '';
}
export function selectionTotal(product: ProductDetail, selected: string[], quantity = 1): number {
  return (cents(product.base_price) + product.groups.flatMap(group => group.options).filter(option => selected.includes(option.id)).reduce((sum, option) => sum + cents(option.additional_price), 0)) * quantity;
}
