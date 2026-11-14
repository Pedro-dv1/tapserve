export async function auditMediaAndLoader(page, { base, output }) {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(base + '/produto-demo.html');
  await page.locator('.menu-product').last().waitFor();
  const names = await page.locator('.menu-product .product-copy strong').allTextContents();
  check(names.length === 3, 'Selected original products');
  const images = [];
  for (const name of names) {
    const card = page.locator('.menu-product').filter({ has: page.getByText(name, { exact: true }) });
    await card.scrollIntoViewIfNeeded();
    await card.locator('img').evaluate(image => image.decode());
    check(await card.locator('img').evaluate(image => image.naturalWidth > 0), `${name}: card image`);
    await page.getByRole('button', { name: `Personalizar ${name}`, exact: true }).click();
    await page.locator('.detail-photo img').evaluate(image => image.decode());
    images.push({ name, source: await page.locator('.detail-photo img').getAttribute('src'), loaded: true });
    check(await page.locator('.image-fallback').count() === 0, `${name}: permanent placeholder`);
    await page.screenshot({ path: `${output}/product-${images.length}-390.png`, fullPage: true });
    await page.getByRole('button', { name: 'Voltar', exact: true }).click();
    await page.locator('.menu-product').last().waitFor();
  }
  let release;
  const pattern = '**/assets/demo-*.js';
  const hold = route => new Promise(resolve => { release = () => route.continue().then(resolve); });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.route(pattern, hold);
  try {
    await page.goto(base + '/produto-demo.html', { waitUntil: 'commit' });
    await page.locator('.brand-loading-mark img').waitFor();
    await page.waitForTimeout(400);
    const logo = await page.locator('.brand-loading-mark img').evaluate(image => ({ width: image.clientWidth, height: image.clientHeight, animation: getComputedStyle(image).animationName }));
    check(Math.abs(logo.width / logo.height - 337 / 441) < .02, 'Original brand proportions');
    check(logo.animation === 'loader-breathe', 'Branded loading animation');
    await page.screenshot({ path: `${output}/preloader-390.png` });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    check(await page.locator('.brand-loading-mark img').evaluate(image => getComputedStyle(image).animationName) === 'none', 'Reduced loader motion');
    check(!await page.locator('.brand-loading-help').isVisible(), 'Motion preference must not bypass the real-loading timeout');
    await page.locator('.brand-loading-help').waitFor({ state: 'visible', timeout: 11000 });
    await page.locator('.brand-loading-mark').waitFor({ state: 'hidden' });
    check(await page.getByRole('link', { name: 'Tentar novamente', exact: true }).isVisible(), 'Slow/failed bootstrap recovery link');
    await page.screenshot({ path: `${output}/preloader-recovery-390.png` });
    check(typeof release === 'function', 'Real module request was delayed');
    await release(); release = undefined;
    await page.getByRole('button', { name: 'Personalizar Suco Natural', exact: true }).waitFor();
    check(await page.locator('.brand-loading').count() === 0, 'Loader retires when the interface starts');
  } finally { if (release) await release(); await page.unroute(pattern, hold); }
  return { images, checks: ['cards and galleries', 'original media paths', 'no permanent placeholders', 'real pending module', 'brand proportions', 'slow load recovery', 'reduced motion', 'ready state removes loader'] };
}
