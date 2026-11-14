export function Demo({ compact = false }: { compact?: boolean }) {
  return <section className={`product-demo${compact ? ' compact-demo' : ''}`} aria-label="Demonstração interativa TapServe">
    <div className="product-demo-layout"><iframe title="Explore o cardápio real do TapServe" src="/produto-demo.html" loading="lazy" /><aside>
      <h3>Seu próximo pedido,<br />do seu jeito.</h3><p>Explore o cardápio, escolha os opcionais e confira o carrinho na interface do produto.</p>
      <ul><li>Navegue por categorias ou busque um prato.</li><li>Personalize e revise as suas escolhas.</li><li>Envie apenas uma simulação e acompanhe os estados.</li></ul>
      <p className="caption">A demonstração funciona em memória. Reiniciar ou recarregar limpa a experiência.</p><a className="text-link" href="/contato">Conhecer no meu estabelecimento →</a>
    </aside></div>
  </section>;
}
