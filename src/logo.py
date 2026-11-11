#!/usr/bin/env python3
"""Generates the DEADFRAME logo (pure paths, no font dependency) + icon."""
import sys, os

L = {  # letters drawn as strokes in a 90x130 cell
    'D': 'M10,10 H50 L80,40 V90 L50,120 H10 Z',
    'E': 'M82,10 H10 V120 H82 M10,65 H64',
    'A': 'M10,122 V38 L38,10 H52 L80,38 V122 M10,80 H80',
    'F': 'M82,10 H10 V122 M10,65 H64',
    'R': 'M10,122 V10 H58 L80,32 V50 L62,68 H10 M50,68 L80,122',
    'M': 'M10,122 V10 L45,64 L80,10 V122',
    'C': 'M82,10 H10 V120 H82',
}
BONE, RED, CYAN, BG = '#e9e6df', '#e5291f', '#39d5d0', '#0a0b0c'


def word(txt, x, y, s=1.0, gap=22, sw=20, col=BONE, extra=''):
    out, cx = [], x
    for ch in txt:
        out.append(f'<path d="{L[ch]}" transform="translate({cx:.1f},{y:.1f}) scale({s})" fill="none" '
                   f'stroke="{col}" stroke-width="{sw}" stroke-linejoin="miter" stroke-miterlimit="2" {extra}/>')
        cx += (90 + gap) * s
    return '\n'.join(out)


def wordmark(bg=True):
    W, H = 1200, 420
    x0, y0 = 107, 145
    xf = x0 + 4 * 112  # start of FRAME
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    if bg:
        p.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    p.append(f'''<defs>
<clipPath id="keep"><rect x="0" y="0" width="{W}" height="{y0+94}"/><rect x="0" y="{y0+110}" width="{W}" height="{H}"/></clipPath>
<clipPath id="band"><rect x="0" y="{y0+94}" width="{W}" height="16"/></clipPath>
</defs>''')
    # viewfinder brackets (top-right one is knocked out of place: the "dead" frame)
    b = 'fill="none" stroke-width="7" stroke-linecap="square"'
    p.append(f'<path d="M60,128 V70 H150" stroke="{BONE}" {b}/>')
    p.append(f'<path d="M60,292 V350 H150" stroke="{BONE}" {b}/>')
    p.append(f'<path d="M1140,292 V350 H1050" stroke="{BONE}" {b}/>')
    p.append(f'<path d="M1050,70 H1140 V128" stroke="{RED}" {b} transform="translate(14,-12) rotate(7 1140 70)"/>')
    # REC dot + tiny REC + timecode ticks
    p.append(f'<circle cx="112" cy="104" r="11" fill="{RED}"/>')
    p.append(word('REC', 134, 92, s=0.19, gap=30, sw=22, col=BONE))
    for i in range(14):
        h = 14 if i % 4 == 0 else 7
        p.append(f'<rect x="{820+i*14}" y="{112-h}" width="3" height="{h}" fill="{BONE}" opacity=".55"/>')
    for i in range(22):
        h = 12 if i % 5 == 0 else 6
        p.append(f'<rect x="{180+i*13}" y="{318}" width="3" height="{h}" fill="{BONE}" opacity=".4"/>')
    p.append(f'<rect x="700" y="316" width="300" height="3" fill="{BONE}" opacity=".4"/>')
    p.append(f'<rect x="700" y="316" width="118" height="9" fill="{RED}"/>')
    # DEAD (solid) + FRAME (with a torn scanline band)
    p.append(word('DEAD', x0, y0))
    p.append(f'<g clip-path="url(#keep)">{word("FRAME", xf, y0)}</g>')
    p.append(f'<g clip-path="url(#band)"><g transform="translate(-7,0)">{word("FRAME", xf, y0, col=CYAN)}</g>'
             f'<g transform="translate(14,0)">{word("FRAME", xf, y0, col=RED)}</g></g>')
    p.append('</svg>')
    return '\n'.join(p)


def icon():
    p = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">']
    p.append(f'<rect width="256" height="256" rx="44" fill="{BG}"/>')
    p.append('''<defs><clipPath id="k"><rect width="256" height="118"/><rect y="138" width="256" height="118"/></clipPath>
<clipPath id="b"><rect y="118" width="256" height="20"/></clipPath></defs>''')
    b = 'fill="none" stroke-width="9" stroke-linecap="square"'
    p.append(f'<path d="M30,74 V30 H74" stroke="{BONE}" {b}/><path d="M30,182 V226 H74" stroke="{BONE}" {b}/>'
             f'<path d="M226,182 V226 H182" stroke="{BONE}" {b}/>'
             f'<path d="M182,30 H226 V74" stroke="{RED}" {b} transform="translate(6,-5) rotate(9 226 30)"/>')
    d = word('D', 38, 70, s=0.9, sw=22)
    f1 = word('F', 140, 70, s=0.9, sw=22)
    p.append(d)
    p.append(f'<g clip-path="url(#k)">{f1}</g>')
    p.append(f'<g clip-path="url(#b)"><g transform="translate(-6,0)">{word("F",140,70,s=0.9,sw=22,col=CYAN)}</g>'
             f'<g transform="translate(12,0)">{word("F",140,70,s=0.9,sw=22,col=RED)}</g></g>')
    p.append(f'<circle cx="52" cy="52" r="9" fill="{RED}"/>')
    p.append('</svg>')
    return '\n'.join(p)


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    open(f'{out}/DEADFRAME-logo.svg', 'w').write(wordmark(True))
    open(f'{out}/logo-transparent.svg', 'w').write(wordmark(False))
    open(f'{out}/DEADFRAME-icon.svg', 'w').write(icon())
