import { renderToString } from 'react-dom/server';
import { App } from './App';
export { routes, notFoundRoute } from './data/routes';
export function render(path: string) { return renderToString(<App path={path} />); }
