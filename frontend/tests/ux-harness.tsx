// Browser-only fixtures exercise the real shared components, never the production bundle.
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Editor } from '../src/features/staff/StaffUI';
import { formSaveResult, requestEditorClose } from '../src/lib/formChanges';
import SearchCombobox from '../src/components/SearchCombobox';
import { MenuFeature } from '../src/features/customer/MenuBrowser';
import '../src/design-system/base.css';
import '../src/design-system/staff.css';
import '../src/design-system/customer.css';

function Harness() {
  const [open, setOpen] = useState(false), [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(false), [error, setError] = useState('');
  const [persisted, setPersisted] = useState('Original'), [writes, setWrites] = useState(0);
  const [ids, setIds] = useState(['a', 'b']);
  const [query, setQuery] = useState(''), [searched, setSearched] = useState(''), [chosen, setChosen] = useState('');
  return <div className="staff-shell"><main className="staff-main"><h1>Teste de interações</h1><button onClick={() => { setIds(['a', 'b']); setOpen(true); }}>Editar</button><label><input type="checkbox" checked={failure} onChange={event => setFailure(event.target.checked)} />Falhar salvamento</label><output data-persisted>{persisted}</output><output data-writes>{writes}</output>
    {open && <Editor title="Editar cadastro" close={() => setOpen(false)} busy={busy}><form onSubmit={event => {
      event.preventDefault(); const form = event.currentTarget; setBusy(true); setError('');
      setTimeout(() => { if (failure) { setError('Não foi possível salvar.'); formSaveResult(form, false); } else { setPersisted(String(new FormData(form).get('name'))); setWrites(value => value + 1); formSaveResult(form, true); setOpen(false); } setBusy(false); }, 200);
    }}><label>Nome<input name="name" defaultValue={persisted} required /></label><label>Preço<input name="price" type="number" defaultValue="10.00" /></label><label><input type="checkbox" name="active" defaultChecked />Ativo</label><label>Imagem<input type="file" name="image" /></label>{ids.map(id => <input key={id} type="hidden" name="options" data-dirty-set value={id} />)}<div className="actions"><button type="button" onClick={() => setIds(value => value.filter(id => id !== 'a'))}>Remover opção</button><button type="button" onClick={() => setIds(value => value.includes('a') ? value : [...value, 'a'])}>Restaurar opção</button></div>{error && <p role="alert">{error}</p>}<div className="actions"><button type="submit" disabled={busy}>Salvar cadastro</button><button className="secondary" type="button" disabled={busy} onClick={requestEditorClose}>Cancelar</button></div><a href="/staff/orders">Ir para pedidos</a></form></Editor>}
    <SearchCombobox label="Buscar produto" value={query} change={setQuery} search={setSearched} suggestions={['Hambúrguer artesanal', 'Hambúrguer duplo'].filter(name => query && name.toLowerCase().includes(query.toLowerCase())).map((name, id) => ({ id: String(id), name }))} select={item => setChosen(item.name)} />
    <output data-search>{searched}</output><output data-chosen>{chosen}</output>
    <div className="call-actions"><form><button className="secondary" type="button">Assumir chamado</button></form><button className="ui-danger" type="button">Cancelar chamado</button></div>
    <div className="popular-features"><MenuFeature popular product={{ id: 'test', name: 'Hambúrguer artesanal', description: 'Preparado na hora', base_price: '12.50', most_ordered: true, ordered_quantity: 5, has_image: false, has_video: false, image_version: '' }} open={setChosen} /></div>
  </main></div>;
}
document.getElementById('root')?.remove();
const root = document.createElement('div'); document.body.append(root); createRoot(root).render(<Harness />);
