import { StrictMode, ViewTransition } from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from './app/ErrorBoundary';
import { App } from './app/App';
import { ToastProvider } from './components/Toast';
import './design-system/base.css';
import './design-system/motion.css';

const root = document.getElementById('root');
if (!root) throw new Error('Application root missing');
createRoot(root).render(<StrictMode><ErrorBoundary><ToastProvider><ViewTransition default="none" update={{ navigation: 'motion-page', default: 'none' }}><App /></ViewTransition></ToastProvider></ErrorBoundary></StrictMode>);
