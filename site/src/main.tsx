import { createRoot, hydrateRoot } from 'react-dom/client';
import { App } from './App';
import { notFoundRoute, routeFor } from './data/routes';
import './styles/site.css';
import './styles/refinements.css';

const root = document.getElementById('root');
if (!root) throw new Error('A página não pôde ser iniciada. Recarregue para tentar novamente.');
const path = window.location.pathname;
const route = routeFor(path);
document.title = `${route?.title ?? notFoundRoute.title} | TapServe`;
const app = <App path={path} />;
if (root.querySelector('[data-site]')) hydrateRoot(root, app); else createRoot(root).render(app);
