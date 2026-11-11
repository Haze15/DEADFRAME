#!/usr/bin/env python3
"""Assemble index.html (logo inliné) puis fabrique l'icône .ico et la ressource .syso pour le .exe."""
import base64, io, os, re, struct, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dist, server = f'{ROOT}/logo', ROOT

html = open(f'{ROOT}/src/game.html', encoding='utf-8').read()
logo = open(f'{dist}/logo-transparent.svg', encoding='utf-8').read()
logo = re.sub(r'<svg ([^>]*?) width="\d+" height="\d+">', r'<svg class="logo" role="img" aria-label="DEADFRAME" \1>', logo, count=1)
logo = logo.replace('id="keep"', 'id="lk"').replace('#keep', '#lk').replace('id="band"', 'id="lb"').replace('#band', '#lb')
icon_svg = open(f'{dist}/DEADFRAME-icon.svg', 'rb').read()
html = html.replace('%%LOGO%%', logo).replace('%%ICON%%', 'data:image/svg+xml;base64,' + base64.b64encode(icon_svg).decode())
open(f'{ROOT}/index.html', 'w', encoding='utf-8').write(html)
# version « page unique » : tous les assets embarqués en base64 (pour une page hébergée sans fichiers annexes)
emb = ''.join(f'<script type="application/octet-stream" id="asset:{f}">{base64.b64encode(open(f"{ROOT}/assets/{f}","rb").read()).decode()}</script>\n' for f in sorted(os.listdir(f'{ROOT}/assets')))
os.makedirs(f'{ROOT}/page', exist_ok=True)
open(f'{ROOT}/page/index.html', 'w', encoding='utf-8').write(html.replace('<script>\n\'use strict\';', emb + '<script>\n\'use strict\';', 1))
print('page unique:', os.path.getsize(f'{ROOT}/page/index.html') // 1024, 'KB')

# ---- icône : entrées PNG multi-tailles
src = Image.open(f'{dist}/DEADFRAME-icon.png').convert('RGBA')
sizes = [16, 24, 32, 48, 64, 128, 256]
imgs = []
for s in sizes:
    b = io.BytesIO(); src.resize((s, s), Image.LANCZOS).save(b, 'PNG'); imgs.append(b.getvalue())
# fichier .ico
ico = struct.pack('<HHH', 0, 1, len(sizes)); off = 6 + 16 * len(sizes)
for s, d in zip(sizes, imgs):
    ico += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(d), off); off += len(d)
open(f'{dist}/DEADFRAME.ico', 'wb').write(ico + b''.join(imgs))

# ---- section .rsrc (COFF amd64) : RT_ICON (3) + RT_GROUP_ICON (14)
grp = struct.pack('<HHH', 0, 1, len(sizes))
for i, (s, d) in enumerate(zip(sizes, imgs)):
    grp += struct.pack('<BBBBHHIH', s % 256, s % 256, 0, 0, 1, 32, len(d), i + 1)
leaves = [(3, i + 1, d) for i, d in enumerate(imgs)] + [(14, 1, grp)]
types = sorted(set(t for t, _, _ in leaves))
DIR, ENT, DATA = 16, 8, 16
size_root = DIR + ENT * len(types)
type_off, o = {}, size_root
for t in types:
    type_off[t] = o; o += DIR + ENT * sum(1 for l in leaves if l[0] == t)
lang_off = []
for _ in leaves:
    lang_off.append(o); o += DIR + ENT
data_off = []
for _ in leaves:
    data_off.append(o); o += DATA
raw_off = []
for _, _, d in leaves:
    raw_off.append(o); o += (len(d) + 7) & ~7
sec = bytearray(o)
def put_dir(at, n): struct.pack_into('<IIHHHH', sec, at, 0, 0, 0, 0, 0, n)
put_dir(0, len(types))
for i, t in enumerate(types):
    struct.pack_into('<II', sec, DIR + ENT * i, t, 0x80000000 | type_off[t])
    idx = [k for k, l in enumerate(leaves) if l[0] == t]
    put_dir(type_off[t], len(idx))
    for j, k in enumerate(idx):
        struct.pack_into('<II', sec, type_off[t] + DIR + ENT * j, leaves[k][1], 0x80000000 | lang_off[k])
relocs = []
for k, (_, _, d) in enumerate(leaves):
    put_dir(lang_off[k], 1)
    struct.pack_into('<II', sec, lang_off[k] + DIR, 0x0409, data_off[k])
    struct.pack_into('<IIII', sec, data_off[k], raw_off[k], len(d), 0, 0)
    relocs.append(data_off[k])
    sec[raw_off[k]:raw_off[k] + len(d)] = d
p_raw = 20 + 40; p_rel = p_raw + len(sec); p_sym = p_rel + 10 * len(relocs)
coff = struct.pack('<HHIIIHH', 0x8664, 1, 0, p_sym, 1, 0, 0)
coff += b'.rsrc\0\0\0' + struct.pack('<IIIIIIHHI', 0, 0, len(sec), p_raw, p_rel, 0, len(relocs), 0, 0x40000040)
coff += bytes(sec)
for r in relocs:
    coff += struct.pack('<IIH', r, 0, 3)  # IMAGE_REL_AMD64_ADDR32NB
coff += b'.rsrc\0\0\0' + struct.pack('<IhHBB', 0, 1, 0, 3, 0) + struct.pack('<I', 4)
open(f'{server}/rsrc_windows_amd64.syso', 'wb').write(coff)
print('ok: index.html', len(html), 'bytes ; syso', len(coff), 'bytes')
