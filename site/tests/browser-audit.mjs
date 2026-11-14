export async function auditPages(page, { base, output, paths, width }) {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const errors = [], requests = [], results = [];
  let missingPage = '';
  const consoleError = message => {
    if (message.type() === 'error' && !(message.location().url === missingPage && message.text().includes('404 (Not Found)'))) errors.push(message.text());
  };
  const pageError = error => errors.push(error.message);
  const request = value => requests.push({ method: value.method(), url: value.url() });
  page.on('console', consoleError); page.on('pageerror', pageError); page.on('request', request);
  try {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    for (const path of paths) {
      missingPage = path.startsWith('/inexistente') ? base + path : '';
      const response = await page.goto(base + path, { waitUntil: 'networkidle' });
      check(response.status() === (path.startsWith('/inexistente') ? 404 : 200), `${width}px ${path}: HTTP ${response.status()}`);
      check(await page.locator('h1').count() === 1, `${path}: H1`);
      check(await page.locator('form').count() === 0, `${path}: contact form`);
      check(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), `${width}px ${path}: horizontal overflow`);
      check(!/\bQR\b|Desativar animações|\b0\d\s*\/\s*\d/u.test(await page.locator('body').innerText()), `${path}: removed copy`);
      check(await page.locator('.eyebrow,.pricing-card,.gallery-options,.hotspot,.segment-number').count() === 0, `${path}: removed decoration`);
      const broken = await page.locator('img').evaluateAll(images => images.filter(image => image.complete && image.naturalWidth === 0).map(image => image.src));
      check(broken.length === 0, `${path}: missing images ${broken}`);
      const header = await page.locator('.header-inner').evaluate(element => [...element.children].filter(child => child.getBoundingClientRect().width > 0).map(child => { const r = child.getBoundingClientRect(); return { left: r.left, right: r.right }; }));
      check(header.every((item, index) => index === 0 || item.left >= header[index - 1].right - 1), `${width}px: header overlaps`);
      for (const phone of await page.locator('.phone-preview').all()) {
        const ratio = await phone.evaluate(element => element.offsetWidth / element.offsetHeight);
        check(ratio > .44 && ratio < .53, `${width}px ${path}: phone ratio ${ratio}`);
        const imageRatio = await phone.locator('img').evaluate(image => image.offsetWidth / image.offsetHeight);
        check(Math.abs(imageRatio - 390 / 844) < .003, `${path}: stretched screen`);
      }
      if (path === '/') {
        const nfc = page.locator('#primeiro-toque');
        check(await nfc.locator('img').count() === 1 && await nfc.locator('button').count() === 0, 'NFC section must contain one original plaque');
        check(await page.locator('.faq-photo').isVisible() === (width >= 1024), 'FAQ photograph only on the desktop two-column layout');
        if (width >= 1024) {
          await page.locator('.faq-photo').scrollIntoViewIfNeeded();
          await page.locator('.faq-photo').evaluate(image => image.decode());
        }
        await page.locator('.faq-section').screenshot({ path: `${output}/faq-section-${width}.png`, animations: 'disabled' });
        await page.locator('.hero').screenshot({ path: `${output}/hero-${width}.png`, animations: 'disabled' });
        await nfc.screenshot({ path: `${output}/nfc-section-${width}.png`, animations: 'disabled' });
      }
      if (path === '/funcionalidades') check(await page.getByText('Acesso para cada responsabilidade', { exact: true }).count() === 0, 'Removed permissions presentation');
      if (path === '/duvidas') {
        check(await page.locator('h1').evaluate(element => getComputedStyle(element).textAlign) === 'center', 'FAQ title alignment');
        check(await page.locator('.accordion summary').first().evaluate(element => getComputedStyle(element).textAlign) !== 'center', 'FAQ questions remain readable on the left');
      }
      if (path === '/demonstracao') {
        check(await page.locator('.demo-notice').count() === 0, 'Removed demo notice');
        const spacing = await page.locator('.demo-full').evaluate(element => {
          const section = element.getBoundingClientRect(), cta = element.querySelector('.section-action > a').getBoundingClientRect();
          return { bottom: section.bottom - cta.bottom, center: Math.abs((cta.left + cta.right) / 2 - (section.left + section.right) / 2) };
        });
        check(spacing.bottom >= 60 && spacing.center < 1, 'Demo CTA spacing and alignment');
      }
      if (path === '/contato' || path === '/suporte') {
        const center = await page.locator('.page-intro h1').evaluate(element => { const r = element.getBoundingClientRect(); return (r.left + r.right) / 2; });
        const pageWidth = await page.evaluate(() => document.documentElement.clientWidth);
        check(Math.abs(center - pageWidth / 2) < 1, `${width}px ${path}: contact title center`);
        check(await page.locator('.page-intro h1').evaluate(element => getComputedStyle(element).textAlign) === 'center', `${path}: title text alignment`);
        const buttons = await page.locator('.contact-buttons > a').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().width));
        check(buttons.length === 2 && Math.abs(buttons[0] - buttons[1]) < 1, `${path}: contact button widths`);
      }
      if (['/', '/contato', '/nfc', '/demonstracao', '/duvidas', '/funcionalidades', '/inexistente/rota'].includes(path)) {
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
        await page.screenshot({ path: `${output}/${path.startsWith('/inexistente') ? '404' : path.slice(1) || 'home'}-${width}.png`, fullPage: true, animations: 'disabled' });
      }
      results.push({ path, width, status: response.status(), overflow: false });
    }
    check(requests.every(request => request.method === 'GET' && new URL(request.url).origin === base && !new URL(request.url).pathname.startsWith('/api/')), 'Demo escaped static, same-origin assets');
    check(errors.length === 0, errors.join('\n'));
    return { results, requests: requests.length, errors };
  } finally { page.removeListener('console', consoleError); page.removeListener('pageerror', pageError); page.removeListener('request', request); }
}

export async function auditInteractions(page, { base, output }) {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const errors = [], requests = [];
  const consoleError = message => { if (message.type() === 'error') errors.push(message.text()); };
  const request = value => requests.push({ method: value.method(), url: value.url() });
  page.on('console', consoleError); page.on('request', request);
  try {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base + '/demonstracao');
    await page.locator('iframe').evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
    const frame = page.frameLocator('iframe');
    await frame.getByRole('button', { name: 'Carrinho', exact: true }).click();
    check(await frame.getByText('Seu carrinho está vazio', { exact: true }).isVisible(), 'Empty cart');
    await frame.getByRole('button', { name: 'Ver cardápio', exact: true }).click();
    await frame.getByRole('button', { name: 'Bebidas', exact: true }).click();
    check(await frame.getByRole('button', { name: 'Personalizar Suco Natural', exact: true }).isVisible(), 'Category filter');
    await frame.getByRole('button', { name: 'Tudo', exact: true }).click();
    await frame.getByRole('button', { name: 'Personalizar Hambúrguer Clássico', exact: true }).click();
    await frame.getByRole('button', { name: /Adicionar ao carrinho/ }).click();
    check((await frame.getByRole('alert').innerText()).includes('Ponto da carne'), 'Required option');
    await frame.getByRole('radio', { name: /Ao ponto/ }).check();
    await frame.getByRole('checkbox', { name: /^Queijo / }).check();
    await frame.getByRole('button', { name: 'Aumentar Hambúrguer Clássico', exact: true }).click();
    await frame.getByRole('button', { name: /Adicionar ao carrinho/ }).click();
    check((await frame.locator('.summary-total').innerText()).includes('57,80'), 'Cart total');
    await frame.getByRole('button', { name: 'Editar Hambúrguer Clássico', exact: true }).click();
    await frame.getByRole('checkbox', { name: /^Queijo / }).uncheck();
    await frame.getByRole('button', { name: /Salvar alterações/ }).click();
    check((await frame.locator('.summary-total').innerText()).includes('49,80'), 'Edited total');
    await frame.getByRole('button', { name: 'Continuar escolhendo', exact: true }).click();
    await frame.getByRole('button', { name: 'Personalizar Batata Frita', exact: true }).click();
    await frame.getByRole('button', { name: /Adicionar ao carrinho/ }).click();
    await frame.getByRole('button', { name: 'Remover Batata Frita', exact: true }).click();
    await frame.getByRole('button', { name: 'Diminuir Hambúrguer Clássico', exact: true }).click();
    check((await frame.locator('.summary-total').innerText()).includes('24,90'), 'Quantity and remove');
    await page.screenshot({ path: `${output}/demo-cart-desktop.png`, fullPage: true });
    await frame.getByRole('button', { name: /Enviar pedido/ }).click();
    check(await frame.locator('.order-batch').count() === 1, 'Local simulated order');
    for (let index = 0; index < 3; index++) await frame.getByRole('button', { name: 'Avançar estado', exact: true }).click();
    await frame.getByRole('button', { name: 'Histórico', exact: true }).click();
    check((await frame.locator('.orders-page').innerText()).includes('Entregue'), 'Status progression');
    await frame.getByRole('button', { name: 'Pedir mais', exact: true }).click();
    await frame.getByRole('button', { name: 'Personalizar Batata Frita', exact: true }).click();
    await frame.getByRole('button', { name: /Adicionar ao carrinho/ }).click();
    await frame.getByRole('button', { name: /Enviar pedido/ }).click();
    check(await frame.locator('.order-batch').count() === 1, 'A new order preserves the delivered history');
    check(await frame.locator('.order-item img').count() === 1 && await frame.locator('.order-item .image-fallback').count() === 0, 'Original product photo in the order');
    await frame.getByRole('button', { name: 'Histórico', exact: true }).click();
    check((await frame.locator('.orders-page').innerText()).includes('Entregue'), 'Delivered order was preserved');
    await frame.getByRole('button', { name: 'Início', exact: true }).click();
    await frame.getByRole('button', { name: 'Chamar garçom', exact: true }).click();
    await frame.getByRole('button', { name: 'Chamar atendente', exact: true }).click();
    await frame.getByRole('dialog').filter({ hasText: 'Atendimento solicitado' }).waitFor();
    await frame.getByRole('button', { name: 'Entendido', exact: true }).click();
    await frame.getByRole('button', { name: 'Pedir a conta', exact: true }).click();
    await frame.getByRole('dialog').filter({ hasText: 'Conta solicitada' }).waitFor();
    await frame.getByRole('button', { name: 'Entendido', exact: true }).click();
    await frame.getByRole('button', { name: 'Reiniciar demonstração', exact: true }).click();
    await page.locator('iframe').evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await frame.getByRole('button', { name: 'Carrinho', exact: true }).click();
    check(await frame.getByText('Seu carrinho está vazio', { exact: true }).isVisible(), 'Demo reset');
    await page.goto(base + '/');
    await page.getByRole('tab', { name: 'Cliente', exact: true }).focus(); await page.keyboard.press('ArrowRight');
    check(await page.getByRole('tab', { name: 'Equipe', exact: true }).getAttribute('aria-selected') === 'true', 'Keyboard tabs');
    await page.locator('summary').first().focus(); await page.keyboard.press('Space');
    check(await page.locator('details').first().getAttribute('open') !== null, 'Keyboard accordion');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('button', { name: 'Abrir menu', exact: true }).click();
    check(await page.getByRole('navigation', { name: 'Navegação mobile' }).isVisible(), 'Mobile menu');
    await page.getByRole('navigation', { name: 'Navegação mobile' }).getByRole('link').first().focus();
    await page.keyboard.press('Escape');
    check(await page.getByRole('button', { name: 'Abrir menu', exact: true }).evaluate(element => element === document.activeElement), 'Mobile focus restoration');
    await page.goto(base + '/duvidas');
    await page.getByLabel('O que você quer saber?').fill('missing-123');
    check(await page.getByText('Nenhuma dúvida encontrada.', { exact: true }).isVisible(), 'FAQ empty search');
    await page.getByRole('button', { name: 'Limpar busca', exact: true }).click();
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(base + '/'); await page.locator('#primeiro-toque').scrollIntoViewIfNeeded();
    await page.locator('#primeiro-toque .revealed').first().waitFor();
    await page.emulateMedia({ reducedMotion: 'reduce' });
    check(await page.locator('.hero h1').evaluate(element => getComputedStyle(element).animationName) === 'none', 'System reduced motion');
    check(await page.evaluate(() => document.cookie === '' && localStorage.length === 0 && sessionStorage.length === 0), 'No storage or cookies');
    check(requests.every(request => request.method === 'GET' && new URL(request.url).origin === base && !new URL(request.url).pathname.startsWith('/api/')), 'Demo made a real API request');
    check(errors.length === 0, errors.join('\n'));
    return { checks: ['categories', 'required options', 'quantity', 'edit/remove', 'exact money totals', 'local order and status', 'service modal', 'bill feedback', 'reset', 'keyboard tabs/FAQ/menu', 'motion preference', 'zero operational requests/storage'], requests: requests.length, errors };
  } finally { page.removeListener('console', consoleError); page.removeListener('request', request); }
}
