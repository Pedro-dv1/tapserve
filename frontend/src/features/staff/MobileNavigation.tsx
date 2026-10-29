import { Icon } from '../../components/Interface';
import type { staffPages } from './navigation';

export default function MobileNavigation({ pages, current }: { pages: ReturnType<typeof staffPages>; current: string | undefined }) {
  const destinations = ['/staff/operation', '/staff/orders', '/staff/calls'];
  const visible = destinations.flatMap(href => pages.filter(page => page.href === href));
  return <div className="staff-mobile-navigation"><nav aria-label="áreas da unidade">{visible.map(page => <a href={page.href} key={page.href} aria-current={page.href === current ? 'page' : undefined}><Icon name={page.icon} /><span>{page.label}</span></a>)}<a href="/staff/more" aria-current={!visible.some(page => page.href === current) ? 'page' : undefined}><Icon name="more" /><span>Mais</span></a></nav></div>;
}
