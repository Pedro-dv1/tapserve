(() => {
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
