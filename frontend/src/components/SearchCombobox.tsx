import { useId, useState } from 'react';

export const normalizeSearch = (value: string) => value.trim().replace(/\s+/g, ' ');
export type SearchSuggestion = { id: string; name: string; detail?: string };

export default function SearchCombobox<T extends SearchSuggestion>({ label, value, change, search, suggestions, select, loading = false, disabled = false, error = '', placeholder = 'Nome do produto' }: { label: string; value: string; change: (value: string) => void; search: (value: string) => void; suggestions: T[]; select: (item: T) => void; loading?: boolean; disabled?: boolean; error?: string; placeholder?: string }) {
  const id = useId();
  const [expanded, setExpanded] = useState(false);
  const [active, setActive] = useState(-1);
  const results = error ? [] : suggestions.slice(0, 6);
  const open = expanded && Boolean(normalizeSearch(value));
  function choose(item: T) { setExpanded(false); setActive(-1); select(item); }
  function submit() { setExpanded(false); setActive(-1); search(normalizeSearch(value)); }
  return <div className="search-combobox staff-search" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setExpanded(false); }}>
    <label htmlFor={id}>{label}</label><div className="search-controls"><input id={id} type="search" role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={`${id}-list`} aria-activedescendant={open && active >= 0 && !loading ? `${id}-option-${active}` : undefined} autoComplete="off" maxLength={100} placeholder={placeholder} value={value} disabled={disabled} onFocus={() => setExpanded(true)} onChange={event => { change(event.target.value); setActive(-1); setExpanded(true); }} onKeyDown={event => {
      if (event.key === 'Escape' && open) { event.preventDefault(); event.stopPropagation(); setExpanded(false); setActive(-1); }
      else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setExpanded(true); if (!loading && results.length) setActive(index => event.key === 'ArrowDown' ? (index + 1) % results.length : (index <= 0 ? results.length : index) - 1); }
      else if (event.key === 'Enter') { event.preventDefault(); if (open && !loading && active >= 0 && results[active]) choose(results[active]); else submit(); }
    }} /><button className="secondary" type="button" disabled={disabled} onClick={submit} aria-label={`Pesquisar: ${label}`}>Buscar</button></div>
    {open && <div className="search-suggestions"><ul id={`${id}-list`} role="listbox" aria-label={`Sugestões: ${label}`} aria-busy={loading}>{!loading && results.map((item, index) => <li key={item.id} id={`${id}-option-${index}`} role="option" aria-selected={active === index} onPointerDown={event => event.preventDefault()} onClick={() => choose(item)}><strong>{item.name}</strong>{item.detail && <span>{item.detail}</span>}</li>)}</ul>{(loading || results.length === 0) && <p role="status">{loading ? 'Buscando…' : error || 'Nenhuma correspondência encontrada.'}</p>}</div>}
  </div>;
}
