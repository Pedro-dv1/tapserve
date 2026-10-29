import { Component } from 'react';
import type { ReactNode } from 'react';

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } { return { failed: true }; }

  render(): ReactNode {
    return this.state.failed
      ? <main><h1>Não foi possível abrir esta tela</h1><p role="alert">Atualize a página para tentar novamente.</p><button onClick={() => window.location.reload()}>Atualizar página</button></main>
      : this.props.children;
  }
}
