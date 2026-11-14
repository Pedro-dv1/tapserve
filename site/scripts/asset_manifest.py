"""Inventory every requested ID without calling a missing asset complete."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs/site'
sheet = (ROOT / 'assets_source/TAPSERVE_ASSET_SHEET_V3.md').read_text(encoding='utf-8')
rows = re.findall(r'^\| ([BFSCVODM]\d{2}) \| `([^`]+)` \| (.*?) \| (.*?) \| (P[01]) \|', sheet, re.M)
assert len(rows) == 70, len(rows)
generated = {entry['id']: entry for entry in json.loads((DOCS / 'GENERATED_ASSETS.json').read_text(encoding='utf-8'))['assets']}
manifest = []
for ident, requested, description, dimensions, priority in rows:
    entry = dict(id=ident, requested=requested, file=None, source=None, page='Ver docs/site/MATRIZ.md', priority=priority, state='pendente', license='Revisão necessária antes de publicação', review='Material não fornecido ou ainda dependente de confirmação')
    if ident in ['B06', 'F11', 'O04', 'C05']:
        entry.update(state='nao_aplicavel', review='Retirado da apresentação comercial por decisão de refinamento NFC. Originais de referência preservados; sem uso público.')
    elif ident in generated:
        item = generated[ident]
        entry.update(file=item['file'], source=item['original'], state='gerado', license=item['license'], review=item['review'], responsive_files=item['responsive_files'])
        if ident == 'F07': entry['review'] = 'Cenário gerado com monitor vazio. Composição com KDS real depende de S13; não é captura nem montagem final aprovada.'
    elif ident.startswith('B'):
        file = next((ROOT / 'site/public/assets/brand').glob(f'{ident}-*.svg'))
        entry.update(file=file.relative_to(ROOT).as_posix(), source='site/assets/originals/brand/', state='real' if ident in ['B01', 'B03'] else 'composto', review='Vetores originais preservados; B02 altera apenas cor do lettering, sem alterar curvas. B05 representa aproximação NFC. Validar variantes antes de lançamento.')
    elif ident in ['F02', 'F10', 'F12']:
        file = next((ROOT / 'site/public/assets/product').glob(f'{ident}-*.webp'))
        entry.update(file=file.relative_to(ROOT).as_posix(), source='assets_source/card/Plaquinha.png + F01; script compose_assets.py', state='composto', review='Pixels da placa original recortados sem recriar arte. F02/F12 são montagens sobre mesa, não instalação fotografada; F10 é crop exato. Revisar luz/escala/recorte/acrílico e modelo físico.')
    elif ident.startswith('C'):
        files = {'C01':'site/src/pages.tsx:Home', 'C02':'site/src/pages.tsx:NfcPage', 'C03':'site/src/components/Demo.tsx', 'C04':'site/src/components/product.tsx:OperationFlow', 'C05':'site/src/components/product.tsx:CardGallery', 'C06':'site/src/components/product.tsx:Showcase'}
        entry.update(file=files[ident], source='Composição DOM da plaquinha original + capturas reais do QA', state='composto', review='Interfaces de cliente, equipe e produção capturadas no TapServe real. Não há tela administrativa inventada. A demo utiliza componentes reais do cliente, isolados em memória.')
    elif ident.startswith('O'):
        file = next((ROOT / 'site/public/assets/social').glob(f'{ident}-*.png'))
        entry.update(file=file.relative_to(ROOT).as_posix(), source='compose_assets.py + pixels da placa original', state='composto', review='1200×630; sem recriar wordmark. Fonte Arial do sistema para copy; aprovar visual antes de lançamento.')
    elif ident in ['V03', 'V04']:
        entry.update(file='site/src/components/Demo.tsx' if ident == 'V03' else 'site/src/components/product.tsx:OperationFlow', source='Transições de UI em CSS e estado local', state='composto', review='Motion em código acionado pelo visitante. Sem vídeo pré-renderizado, rede ou pedidos reais.')
    elif ident in ['V02', 'M01', 'M02', 'M03']:
        entry['review'] = 'ADIADO por decisão V3 e usuário. Não produzido, não é bloqueio desta versão.'
    elif ident == 'V01': entry['review'] = 'Opcional não produzido. F01 estático e movimento sutil em código substituem vídeo atmosférico.'
    elif ident == 'F03': entry['review'] = 'Opcional dispensado nesta versão; aproximação NFC adiada. Sem telefone tocando na placa.'
    elif ident == 'F08': entry['review'] = 'Vista adicional de 45° fiel requer foto/arte aprovada. Não inventar outro ângulo a partir de única referência.'
    elif ident == 'F09': entry['review'] = 'Vista superior depende da arte plana/dimensões do modelo real, ainda não fornecidas.'
    elif ident == 'F11': entry['review'] = 'NÃO APLICÁVEL ao original sem QR. Variante com QR aguarda aprovação; nenhum QR falso criado.'
    elif ident.startswith('S'):
        captures = list((ROOT / 'site/public/assets/screenshots').glob(f'{ident}-*.png'))
        if captures:
            entry.update(file=captures[0].relative_to(ROOT).as_posix(), source='TapServe QA local, captura via playwright-local MCP em 13/11/2026', state='real', review='Interface original, dados sintéticos do QA. Acesso NFC legítimo com admissão normal. Nenhum pedido, chamado, pagamento ou mesa criado para captura. Sem token na imagem.')
        else:
            entry['review'] = 'Não capturada nem exibida como screenshot. S05 exige confirmar pedido; outras telas dependem de estados ou acesso não utilizado nesta revisão. Nenhuma substituição fictícia.'
        if ident == 'S19': entry['review'] += ' Relatórios não comprovados; recurso não anunciado.'
    manifest.append(entry)
(DOCS / 'TAPSERVE_ASSET_MANIFEST_V3.json').write_text(json.dumps(dict(date='2026-11-13', items=manifest), ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['# Manifesto completo de assets V3', '', '70 IDs auditados. Sete capturas reais do QA foram obtidas no refinamento de 13/11/2026. Itens retirados da comunicação comercial são não aplicáveis; originais permanecem preservados.', '', '| ID | Arquivo / implementação | Estado | Origem e revisão |', '|---|---|---|---|']
for entry in manifest:
    lines.append(f"| {entry['id']} | `{entry['file'] or '—'}` | {entry['state']} | {entry['review']} |")
lines += ['', 'Fontes/originais em `site/assets/originals/`, derivados públicos em `site/public/assets/`. Licenças, prioridades, origem e caminhos responsivos detalhados no JSON. Prompts de geração em `IMAGE_PROMPTS.md`.', '', 'B02 é variante técnica de cor; ainda requer aprovação. F02/F12 mantêm arte vertical preta e base, conforme referência soberana. A cor branca/horizontal dos documentos anteriores não foi aplicada.', '', 'O01–O05 usam composição em Pillow autorizada pelo V3 §3. Não dependem de navegador nem de geração de lettering. Nenhuma marca de concorrente utilizada.']
(DOCS / 'ASSET_MANIFEST.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
assert len(manifest) == 70 and len({entry['id'] for entry in manifest}) == 70
print('Manifesto de 70 IDs atualizado.')
