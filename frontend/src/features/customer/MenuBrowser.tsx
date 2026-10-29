import { useEffect, useState } from 'react';
import { ApiError, record, text } from '../../lib/api';
import { Button, EmptyState, ErrorState, Icon, LoadingSkeleton, PopularityBadge, ProductImage } from '../../components/Interface';
import { brl, decodeProduct } from './menuData';
import type { Product } from './menuData';
import { MenuCache } from './menuCache';
export { brl, cents, decodeDetail } from './menuData';
export type { Product, ProductDetail } from './menuData';
export { OptionChoices } from './ProductSelection';

export default function MenuBrowser({ open, active = true, revision = '0' }: { open: (id: string) => void; active?: boolean; revision?: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [layout, setLayout] = useState<'EDITORIAL' | 'COMPACT'>('COMPACT');
  const [hero, setHero] = useState<Product | null>(null);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [category, setCategory] = useState('');
  const [categoryPage, setCategoryPage] = useState(1);
  const [categoryNext, setCategoryNext] = useState(false);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [previous, setPrevious] = useState(false);
  const [popular, setPopular] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [cache] = useState(() => new MenuCache());
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') setReload(value => value + 1); }, 30_000);
    const refresh = () => { if (document.visibilityState === 'visible') setReload(value => value + 1); };
    document.addEventListener('visibilitychange', refresh);
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', refresh); };
  }, [active]);
  useEffect(() => {
    const timer = window.setTimeout(() => { setQuery(search.trim()); setPage(1); }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController(); setLoading(true); setError('');
    void cache.get(`/api/v1/public/menu/?page=${page}&popular=${popular}&search=${encodeURIComponent(query)}${category ? `&category=${encodeURIComponent(category)}` : ''}`, `${revision}:${reload}`, controller.signal).then(row => {
      if (controller.signal.aborted) return;
      if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
      const presentation = row.presentation === undefined ? { layout: 'COMPACT', hero: null } : record(row.presentation);
      if (presentation.layout !== 'EDITORIAL' && presentation.layout !== 'COMPACT') throw new Error('Apresentação inválida.');
      setLayout(presentation.layout); setHero(presentation.hero == null ? null : decodeProduct(presentation.hero));
      setProducts(row.results.map(decodeProduct)); setNext(typeof row.next === 'string'); setPrevious(typeof row.previous === 'string');
    }).catch((cause: unknown) => { if (!controller.signal.aborted) { if (cause instanceof ApiError && cause.status === 404 && page > 1) setPage(1); else setError(cause instanceof Error ? cause.message : 'Não foi possível carregar o cardápio.'); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, query, category, popular, reload, revision, active]);
  useEffect(() => { setCategoryPage(1); setCategories([]); }, [revision]);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void cache.get(`/api/v1/public/categories/?page=${categoryPage}`, `${revision}:${reload}`, controller.signal).then(row => {
      if (controller.signal.aborted) return;
      if (!Array.isArray(row.results)) throw new Error('Resposta inválida do serviço.');
      const incoming = row.results.map((value: unknown) => { const item = record(value); return { id: text(item.id), name: text(item.name) }; });
      setCategories(values => categoryPage === 1 ? incoming : [...values.filter(value => !incoming.some(item => item.id === value.id)), ...incoming]);
      setCategoryNext(typeof row.next === 'string');
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Não foi possível carregar categorias.'); });
    return () => controller.abort();
  }, [categoryPage, reload, revision, active]);
  return <section className={`menu-page menu-${layout.toLowerCase()}`} aria-label="Cardápio">
    <form className="menu-search" role="search" onSubmit={event => { event.preventDefault(); setQuery(search.trim()); setPage(1); }}>
      <Icon name="search" /><label className="sr-only" htmlFor="menu-search">Buscar no cardápio</label>
      <input id="menu-search" name="search" type="search" maxLength={100} placeholder="Buscar no cardápio..." value={search} onChange={event => setSearch(event.target.value)} />
    </form>
    <nav className="category-chips" aria-label="Categorias">
      <button className={`category-chip ${category === '' && !popular ? 'selected' : ''}`} aria-pressed={category === '' && !popular} onClick={() => { setCategory(''); setPopular(false); setPage(1); }}>Tudo</button>
      <button className={`category-chip ${popular ? 'selected' : ''}`} aria-pressed={popular} onClick={() => { setPopular(value => !value); setPage(1); }}>Mais pedidos</button>
      {categories.map(row => <button key={row.id} className={`category-chip ${category === row.id ? 'selected' : ''}`} aria-pressed={category === row.id} onClick={event => { setCategory(row.id); setPage(1); document.getElementById('menu-results')?.scrollIntoView({ block: 'start' }); event.currentTarget.scrollIntoView({ block: 'nearest', inline: 'center' }); }}>{row.name}</button>)}
      {categoryNext && <button className="category-chip" onClick={() => setCategoryPage(value => value + 1)}>Mais categorias <Icon name="plus" size={16} /></button>}
    </nav>
    {loading && products.length === 0 ? <LoadingSkeleton /> : error ? <ErrorState message={error} retry={() => setReload(value => value + 1)} /> : <>
      {hero && !query && !category && !popular && page === 1 && <article className="menu-feature"><button className="feature-image-action" aria-label={`Conhecer ${hero.name}`} onClick={() => open(hero.id)}><ProductImage key={hero.image_version} version={hero.image_version} id={hero.id} name={hero.name} hasImage={hero.has_image} className="feature-photo" /></button><div className="feature-copy"><h2>{hero.name}</h2>{hero.description && <p>{hero.description}</p>}<div><strong>{brl(hero.base_price)}</strong><button onClick={() => open(hero.id)}>Conhecer o prato <Icon name="arrow" size={16} /></button></div></div></article>}
      <div className="section-heading" id="menu-results"><h1>{popular ? 'Mais pedidos' : query ? 'Resultados da busca' : category ? categories.find(value => value.id === category)?.name ?? 'Cardápio' : 'Cardápio'}</h1>{(popular || category || query) && <button className="plain-action" onClick={() => { setPopular(false); setCategory(''); setSearch(''); setQuery(''); setPage(1); }}>Ver todos <Icon name="chevron" size={16} /></button>}</div>
      {products.length === 0 ? <EmptyState title={query ? 'Nenhum resultado' : 'Nenhum produto disponível'}>{query ? 'Tente outro nome para encontrar seu pedido.' : 'Confira outra categoria ou solicite ajuda à equipe.'}</EmptyState> : <ul className="menu-products">{products.map(product => <ProductCard key={product.id} product={product} open={open} />)}</ul>}
      {(previous || next) && <div className="pagination"><>{previous && <Button secondary disabled={loading} onClick={() => setPage(value => value - 1)}>Anterior</Button>}</><span>Página {page}</span><>{next && <Button secondary disabled={loading} onClick={() => setPage(value => value + 1)}>Próxima</Button>}</></div>}
    </>}
  </section>;
}
export function ProductCard({ product, open }: { product: Product; open: (id: string) => void }) {
  return <li className="menu-product"><div className="product-main"><div className="product-cover"><button className="product-cover-open" aria-label={`Ver ${product.name}`} onClick={() => open(product.id)}><ProductImage key={product.image_version} version={product.image_version} id={product.id} name={product.name} hasImage={product.has_image} /></button></div><button className="product-copy" onClick={() => open(product.id)}><strong>{product.name}</strong><span>{product.description}</span>{product.most_ordered && <PopularityBadge />}</button></div><div className="product-side"><strong className="price">{brl(product.base_price)}</strong><button className="icon-button add-product" aria-label={`Personalizar ${product.name}`} onClick={() => open(product.id)}><Icon name="plus" /></button></div></li>;
}
