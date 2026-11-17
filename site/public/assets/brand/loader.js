(() => {
  const entrance = document.getElementById('site-preloader');
  if (entrance) {
    const content = document.getElementById('root');
    const started = performance.now();
    let finished = false;
    let readyTimer;
    const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dismiss = () => {
      if (finished) return;
      finished = true;
      window.clearTimeout(deadline);
      window.clearTimeout(readyTimer);
      window.removeEventListener('load', ready);
      if (content) content.inert = false;
      entrance.classList.add('is-finished');
      window.setTimeout(() => { entrance.hidden = true; }, reducedMotion() ? 0 : 180);
    };
    const ready = () => {
      window.clearTimeout(readyTimer);
      readyTimer = window.setTimeout(dismiss, reducedMotion() ? 0 : Math.max(0, 600 - (performance.now() - started)));
    };
    // A failed or slow bundle must not keep the prerendered site covered.
    const deadline = window.setTimeout(dismiss, 1600);
    entrance.hidden = false;
    if (content) content.inert = true;
    window.addEventListener('load', ready, { once: true });
    if (document.readyState === 'complete') ready();
    return;
  }
  const root = document.getElementById('product-root');
  const panel = root?.querySelector('.brand-loading');
  const mark = panel?.querySelector('.brand-loading-mark');
  const help = panel?.querySelector('.brand-loading-help');
  if (!panel || !mark || !help) return;
  // Loading timing must survive the product's reduced-motion CSS.
  help.hidden = true;
  const appearance = window.setTimeout(() => { if (panel.isConnected) mark.hidden = false; }, 180);
  const recovery = window.setTimeout(() => { if (panel.isConnected) { mark.hidden = true; help.hidden = false; } }, 8000);
  const observer = new MutationObserver(() => {
    if (!panel.isConnected) {
      window.clearTimeout(appearance);
      window.clearTimeout(recovery);
      observer.disconnect();
    }
  });
  observer.observe(root, { childList: true });
})();
