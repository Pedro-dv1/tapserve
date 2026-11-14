import { StrictMode, ViewTransition } from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from './app/ErrorBoundary';
import { App } from './app/App';
import { ToastProvider } from './components/Toast';
import './design-system/base.css';
import { reportRecoverableError } from './lib/recoverableError';

const root = document.getElementById('root');
if (!root) throw new Error('Application root missing');
createRoot(root, { onRecoverableError: reportRecoverableError }).render(<StrictMode><ErrorBoundary><ToastProvider><ViewTransition default="none" update={{ navigation: 'motion-page', default: 'none' }}><App /></ViewTransition></ToastProvider></ErrorBoundary></StrictMode>);
