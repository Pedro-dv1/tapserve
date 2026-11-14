"""Compose supplied brand pixels, never synthesize product lettering or a QR."""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public' / 'assets'
SOURCE = Image.open(ROOT / 'assets/originals/card/Plaquinha.png').convert('RGBA')
mask = Image.new('L', SOURCE.size)
ImageDraw.Draw(mask).polygon([(190, 145), (204, 126), (811, 202), (823, 217), (856, 1257), (879, 1290), (884, 1304), (255, 1376), (228, 1368), (109, 1296), (106, 1280), (226, 1253)], fill=255)
SOURCE.putalpha(mask)
SOURCE.resize((520, 780), Image.Resampling.LANCZOS).save(PUBLIC / 'product/plaque-cutout.webp', lossless=True)
background = Image.open(PUBLIC / 'photography/F01-hero-restaurant-wide.webp').convert('RGBA')
scene = ImageOps.fit(background, (1280, 960), centering=(.5, .65))
product = SOURCE.resize((500, 750), Image.Resampling.LANCZOS)
shadow = Image.new('RGBA', scene.size)
ImageDraw.Draw(shadow).ellipse((655, 824, 1165, 902), fill=(0, 0, 0, 95))
scene = Image.alpha_composite(scene, shadow.filter(ImageFilter.GaussianBlur(18)))
scene.alpha_composite(product, (640, 190))
scene.convert('RGB').save(PUBLIC / 'product/F02-card-fixed-on-table.webp', quality=90)
wide_scene = ImageOps.fit(background, (1600, 1200), centering=(.72, .6))
wide_scene.alpha_composite(SOURCE.resize((420, 630), Image.Resampling.LANCZOS), (1020, 540))
wide_scene.convert('RGB').save(PUBLIC / 'product/F12-card-lifestyle-table.webp', quality=90)
macro = Image.open(ROOT / 'assets/originals/card/Plaquinha.png').crop((310, 465, 760, 960))
macro = ImageOps.fit(macro, (1000, 750))
macro.save(PUBLIC / 'product/F10-card-macro-nfc.webp', quality=94)
brand = (PUBLIC / 'brand/B01-logo-wordmark-black.svg').read_text(encoding='utf-8')
light = re.sub(r'(<path id="TapServe-lettering"[^>]*?fill=")url\(#letter-color\)', r'\1#ffffff', brand)
assert light != brand, 'Original wordmark lettering path not found'
(PUBLIC / 'brand/B02-logo-wordmark-light.svg').write_text(light, encoding='utf-8')
icons = {
    'B05-icon-nfc.svg': 'M9 7a7 7 0 0 1 0 10M13 4a11 11 0 0 1 0 16M5 10a3 3 0 0 1 0 4',
}
for name, path in icons.items():
    (PUBLIC / 'brand' / name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#111111" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="{path}"/></svg>', encoding='utf-8')
assert Image.open(PUBLIC / 'product/plaque-cutout.webp').mode == 'RGBA'
print('B02/B05 + exact-pixel plaque cutout, F02/F12 composites and F10 crop generated; fidelity review required.')

social = PUBLIC / 'social'
social.mkdir(exist_ok=True)
def font(size):
    for name in ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError('Install an authorized system font for social cover text.')

covers = [
    ('O01-og-default', ['Seu atendimento', 'começa com', 'um toque.'], 'NFC · Cardápio · Pedidos · Operação'),
    ('O02-og-nfc', ['Um ponto de partida', 'na sua mesa.'], 'A placa original. O acesso à experiência.'),
    ('O03-og-features', ['Uma operação.', 'Diferentes', 'perspectivas.'], 'Cliente · Equipe · Cozinha · Administração'),
    ('O05-og-demo', ['Explore. Escolha.', 'Experimente.'], 'Demonstração local · Nenhum pedido real'),
]
for name, lines, subtitle in covers:
    canvas = Image.new('RGBA', (1200, 630), '#151713')
    draw = ImageDraw.Draw(canvas)
    draw.line((60, 95, 1140, 95), fill='#484a40', width=1)
    draw.text((60, 48), 'TECNOLOGIA À MESA', font=font(14), fill='#e5a62b')
    draw.text((1000, 48), name[:3] + ' / SITE', font=font(14), fill='#b4b8a9')
    # The brand is present in the exact original plaque pixels, never reset as type.
    canvas.alpha_composite(SOURCE.resize((400, 600), Image.Resampling.LANCZOS), (800, 20))
    for index, line in enumerate(lines):
        draw.text((60, 182 + index * 78), line, font=font(64), fill='#e5a62b' if index == len(lines) - 1 else '#ffffff')
    draw.text((60, 550), subtitle, font=font(19), fill='#c8cbbb')
    canvas.convert('RGB').save(social / f'{name}.png', optimize=True)
    assert Image.open(social / f'{name}.png').size == (1200, 630)
print('O01–O05 generated at 1200×630 with exact original brand pixels in the plaque.')
