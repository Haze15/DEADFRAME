"""Arbres morts (champ de bataille 14-18) -> arbre_mort_1..4.glb
Origine au pied du tronc, au sol. Y en haut, mètres. Le bas des racines descend un peu sous le sol (à enterrer)."""
import json, struct, io, math, numpy as np
from PIL import Image
S = 512
def png(a):
    b = io.BytesIO(); Image.fromarray((np.clip(a, 0, 1)*255).astype(np.uint8)).save(b, 'PNG', optimize=True); return b.getvalue()
def noise(cx, cy, seed):
    g = np.tile(np.random.default_rng(seed).random((cy, cx)), (3, 3))
    return np.asarray(Image.fromarray((g*255).astype(np.uint8)).resize((S*3, S*3), Image.BICUBIC), float)[S:2*S, S:2*S]/255
def fbm(seed, sx=1, sy=1): return sum(noise(c*sx, c*sy, seed+i)*a for i, (c, a) in enumerate([(4, .5), (8, .25), (16, .13), (32, .07), (64, .05)]))
yy, xx = np.mgrid[0:S, 0:S]/S
# écorce : fissures verticales (V = le long du tronc), gris-brun, traces de brûlure
fis = noise(40, 6, 1)                                         # étiré dans le sens du tronc
ridges = np.clip((fis-.35)*2.2, 0, 1)
ecorce = np.array([.27, .24, .21])*(.55+.55*ridges[..., None]) * (.85+.3*fbm(2)[..., None])
burn = np.clip((fbm(3)-.52)*3, 0, 1)[..., None]
ecorce = ecorce*(1-.7*burn) + np.array([.03, .025, .02])*burn
ecorce = np.where((noise(90, 14, 4) > .83)[..., None], ecorce*.55, ecorce)        # crevasses profondes
# bois éclaté : fibres claires le long de V, salies
fib = noise(120, 6, 5)*.6 + noise(40, 3, 6)*.4
eclate = np.array([.62, .55, .42])*(.7+.45*fib[..., None]) * (.8+.25*fbm(7)[..., None])
eclate = eclate*(1-.4*np.clip((fbm(8)-.55)*3, 0, 1)[..., None])
TEX = {'Ecorce': png(ecorce), 'Bois_eclate': png(eclate)}

class Tree:
    def __init__(s, seed): s.G = {}; s.rng = np.random.default_rng(seed)
    def g(s, m): return s.G.setdefault(m, ([], [], [], []))
    def tube(s, pts, radii, mat='Ecorce', seg=9, lobes=0.0, cap=None, vofs=0.0):
        """tube le long d'une polyligne 3D ; cap : None (ouvert), 'pointe', 'casse' (bout éclaté)"""
        P = [np.array(p, float) for p in pts]; n = len(P)
        T = [(P[min(i+1, n-1)]-P[max(i-1, 0)]) for i in range(n)]; T = [t/np.linalg.norm(t) for t in T]
        ref = np.array([1.0, 0, 0]) if abs(T[0][0]) < .9 else np.array([0, 0, 1.0])
        Nn = np.cross(T[0], ref); Nn /= np.linalg.norm(Nn); frames = []
        for i in range(n):                                    # transport parallèle
            if i: Nn = Nn - T[i]*np.dot(Nn, T[i]); Nn /= np.linalg.norm(Nn)
            frames.append((Nn, np.cross(T[i], Nn)))
        Pm, Nm, Um, Im = s.g(mat); b0 = len(Pm); v = vofs; ph = s.rng.uniform(0, 6.3)
        for i in range(n):
            if i: v += np.linalg.norm(P[i]-P[i-1])
            N1, N2 = frames[i]; r = radii[i]
            for k in range(seg+1):
                a = 2*math.pi*k/seg
                mod = 1 + lobes*math.cos(3*a+ph) + .06*math.sin(5*a+i*1.7+ph)
                d = N1*math.cos(a)+N2*math.sin(a)
                Pm.append(tuple(P[i]+d*r*mod)); Nm.append(tuple(d)); Um.append((k/seg*max(1, round(r*2*math.pi/.5)), v*.8))
        for i in range(n-1):
            for k in range(seg):
                a = b0+i*(seg+1)+k; b = a+seg+1; Im.extend([a, b, a+1, a+1, b, b+1])
        tip, tipd, tr = P[-1], T[-1], radii[-1]
        if cap == 'pointe':
            ci = len(Pm); Pm.append(tuple(tip+tipd*tr*3)); Nm.append(tuple(tipd)); Um.append((.5, v*.8+.2))
            base = b0+(n-1)*(seg+1)
            for k in range(seg): Im.extend([base+k, ci, base+k+1])
        elif cap == 'casse':
            s.splinters(tip, tipd, frames[-1], tr)
        return v
    def splinters(s, c, d, fr, r, count=None):
        """cassure : plateau de bois éclaté + échardes pointues"""
        N1, N2 = fr; seg = 9
        Pm, Nm, Um, Im = s.g('Bois_eclate'); ci = len(Pm); Pm.append(tuple(c)); Nm.append(tuple(d)); Um.append((.5, .5))
        for k in range(seg+1):
            a = 2*math.pi*k/seg; q = c+(N1*math.cos(a)+N2*math.sin(a))*r*1.15 - d*s.rng.uniform(0, r*.25)
            Pm.append(tuple(q)); Nm.append(tuple(d)); Um.append((.5+.5*math.cos(a), .5+.5*math.sin(a)))  # plateau
        for k in range(seg): Im.extend([ci, ci+1+k, ci+2+k])
        for _ in range(count or max(4, int(r*40))):           # échardes
            a = s.rng.uniform(0, 2*math.pi); rr = r*s.rng.uniform(.2, .95)
            base = c+(N1*math.cos(a)+N2*math.sin(a))*rr
            L = r*s.rng.uniform(.5, 2.6)*(1.2-rr/r*.4); w = r*s.rng.uniform(.12, .35)
            out = (N1*math.cos(a)+N2*math.sin(a))*s.rng.uniform(0, .45)
            tipd = d+out+s.rng.normal(0, .12, 3); tipd /= np.linalg.norm(tipd)
            tg = np.cross(tipd, N1*math.cos(a)+N2*math.sin(a)); tg /= max(np.linalg.norm(tg), 1e-6)
            rad = np.cross(tg, tipd)
            q = [base+tg*w, base-tg*w, base+rad*w*.6, base-rad*w*.6]; t = base+tipd*L
            b = len(Pm)
            for p in q+[t]: Pm.append(tuple(p)); Um.append((s.rng.random(), s.rng.random()))
            for p in q: nn = p-base; Nm.append(tuple(nn/max(np.linalg.norm(nn), 1e-6)))
            Nm.append(tuple(tipd))
            for i0, i1 in ((0, 2), (2, 1), (1, 3), (3, 0)): Im.extend([b+i0, b+i1, b+4])
    def branch(s, start, d, L, r0, depth, broken_p=.5, up=.25):
        """branche courbe ; renvoie points/rayons, et lance les sous-branches"""
        rng = s.rng; n = max(4, int(L/.35)); pts, radii = [], []; p = np.array(start, float); d = np.array(d, float); d /= np.linalg.norm(d)
        broken = rng.random() < broken_p
        Lr = L*(rng.uniform(.45, .8) if broken else 1)
        for i in range(n+1):
            t = i/n; pts.append(p.copy()); radii.append(max(r0*(1-t*(.55 if broken else .9)), .008))
            d = d + rng.normal(0, .18, 3) + np.array([0, up, 0])*.15; d /= np.linalg.norm(d); p = p + d*Lr/n
        s.tube(pts, radii, seg=7 if r0 > .05 else 5, cap='casse' if broken else 'pointe')
        if depth > 0:
            for _ in range(rng.integers(1, 4)):
                k = rng.integers(1, n); dd = (pts[min(k+1, n)]-pts[k]); dd /= np.linalg.norm(dd)
                side = np.cross(dd, rng.normal(0, 1, 3)); side /= np.linalg.norm(side)
                nd = dd*.5 + side*.8 + np.array([0, .25, 0])
                s.branch(pts[k], nd, Lr*rng.uniform(.3, .55), radii[k]*.55, depth-1, broken_p, up)
    def trunk(s, H, r0, lean=(0, 0), top='casse', bends=.08, lobes=.12):
        rng = s.rng; n = max(6, int(H/.4)); pts, radii = [], []; p = np.zeros(3)
        d = np.array([lean[0], 1, lean[1]], float); d /= np.linalg.norm(d)
        for i in range(n+1):
            t = i/n; pts.append(p.copy())
            radii.append(r0*(1.0-.55*t) * (1+.5*max(0, .12-t)/.12))        # évasement au pied
            d = d + rng.normal(0, bends, 3)*np.array([1, 0, 1]); d /= np.linalg.norm(d); p = p + d*H/n
        pts[0] = pts[0] - np.array([0, .25, 0])                            # enterré
        s.tube(pts, radii, seg=11, lobes=lobes, cap=top)
        for k in range(5):                                                 # racines apparentes
            a = 2*math.pi*k/5 + rng.uniform(-.3, .3); hz = np.array([math.cos(a), 0, math.sin(a)])
            L = rng.uniform(.7, 1.3); ts = np.linspace(0, 1, 6)
            rp = [np.array([0, .45, 0]) + hz*(r0*.3 + L*t) + np.array([0, -(.45+.5*L)*t**1.4, 0]) for t in ts]
            s.tube(rp, [r0*.55*(1-.55*t) for t in ts], seg=7, cap='pointe')
        return pts, radii
    def fix_winding(s):
        for m, (Pm, Nm, Um, Im) in s.G.items():
            P = np.array(Pm); N = np.array(Nm); I = np.array(Im).reshape(-1, 3)
            fn = np.cross(P[I[:, 1]]-P[I[:, 0]], P[I[:, 2]]-P[I[:, 0]]); bad = (fn*N[I].sum(1)).sum(1) < 0
            I[bad] = I[bad][:, [0, 2, 1]]; Im[:] = I.ravel().tolist()
    def write(s, path, name):
        s.fix_winding()
        _src = "class _M:\n" + open('tools/modeles/make_meubles.py').read().split("class Mesh:\n")[1].split("\nD = '")[0]
        _src = _src.replace("'roughnessFactor': .85 if m == 'Bois' else .95", "'roughnessFactor': .95")
        ns = dict(globals()); exec(_src, ns); m = ns['_M'](); m.G = {k: v for k, v in s.G.items() if v[3]}; m.write(path, name)

D = 'tools/modeles/'
# 1. grand fût cassé net, quelques moignons
t = Tree(11); pts, rad = t.trunk(8.0, .34, top='casse', bends=.04)
for k in (7, 10, 13, 16):
    a = t.rng.uniform(0, 6.3); t.branch(pts[k], (math.cos(a), .35, math.sin(a)), t.rng.uniform(.5, 1.2), rad[k]*.35, 0, broken_p=.9)
t.write(D+'arbre_mort_1.glb', 'ArbreMort1')
# 2. arbre décharné, branches nues tordues
t = Tree(22); pts, rad = t.trunk(6.5, .3, top='casse', bends=.07)
for k in (8, 10, 11, 13, 14):
    a = t.rng.uniform(0, 6.3); t.branch(pts[k], (math.cos(a), .7, math.sin(a)), t.rng.uniform(1.8, 3.2), rad[k]*.5, 2, broken_p=.45, up=.4)
t.write(D+'arbre_mort_2.glb', 'ArbreMort2')
# 3. souche fendue
t = Tree(33); pts, rad = t.trunk(1.7, .42, top=None, bends=.03, lobes=.18)
fr_d = pts[-1]-pts[-2]; fr_d /= np.linalg.norm(fr_d)
t.splinters(pts[-1], fr_d, (np.array([1., 0, 0]), np.array([0, 0, 1.])), rad[-1], count=13)
t.branch(pts[3], (.9, .5, .2), 1.4, .09, 0, broken_p=1.0)
t.write(D+'arbre_mort_3.glb', 'ArbreMort3')
# 4. arbre penché, à moitié arraché, grosse branche cassée
t = Tree(44); pts, rad = t.trunk(7.0, .32, lean=(.55, .15), top='casse', bends=.05)
for k in (6, 9, 11, 13):
    a = t.rng.uniform(0, 6.3); t.branch(pts[k], (math.cos(a), .5, math.sin(a)), t.rng.uniform(1.5, 2.6), rad[k]*.45, 1, broken_p=.55, up=.5)
t.write(D+'arbre_mort_4.glb', 'ArbreMort4')
