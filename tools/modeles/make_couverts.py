"""Couverts pour le no man's land de la carte Front -> tools/modeles/fr_*.glb
Épave de char, canon de campagne, nid de sacs de sable, tronc abattu, cheval de frise, pile de caisses.
Origine au sol au centre, Y en haut, mètres. À lancer depuis la racine du dépôt."""
import json, struct, io, math, numpy as np
from PIL import Image
D = 'tools/modeles/'
ns = {}; exec(open(D+'make_trench.py').read().split("\nD = '")[0], ns)          # textures Bois, Sacs, Terre + sac de sable
an = {}; exec(open(D+'make_arbres.py').read().split("\nD = '")[0], an)           # écorce, bois éclaté, tubes
S = 512; rng = np.random.default_rng(1914)
def png(a):
    b = io.BytesIO(); Image.fromarray((np.clip(a, 0, 1)*255).astype(np.uint8)).save(b, 'PNG', optimize=True); return b.getvalue()
fbm = lambda seed: ns['fbm'](S, seed); noise = lambda cells, seed: ns['noise'](S, cells, seed)
yy, xx = np.mgrid[0:S, 0:S]/S
# métal rouillé et brûlé, plaques rivetées (0,5 m)
rust = np.clip((fbm(70)-.42)*2.4, 0, 1)[..., None]; burn = np.clip((fbm(71)-.55)*3, 0, 1)[..., None]
metal = np.array([.20, .19, .17])*(1-rust) + np.array([.36, .17, .07])*(.7+.6*noise(90, 72)[..., None])*rust
metal = metal*(1-.75*burn) + .02*burn
seam = ((np.abs((xx*4) % 1-.5) > .485) | (np.abs((yy*4) % 1-.5) > .485))[..., None]
riv = ((np.hypot(((xx*4) % 1-.5)*1.0, ((yy*32) % 1-.5)/8) < .0) | ((np.abs(((xx*4) % 1)-.06) < .012) & (np.abs(((yy*32) % 1)-.5) < .2)))[..., None]
metal = np.where(seam, metal*.55, metal); metal = np.where(riv, metal*1.35+.03, metal)
# chenilles : patins striés
pat = ((yy*12) % 1); chen = np.array([.17, .14, .11])*(.6+.6*(pat > .15)[..., None])*(.8+.4*fbm(73)[..., None]) + np.array([.12, .06, .02])*rust
# peinture kaki écaillée (canon)
chip = (fbm(74) > .6)[..., None]
kaki = np.where(chip, np.array([.30, .16, .08])*(.7+.5*noise(60, 75)[..., None]), np.array([.24, .25, .17])*(.8+.3*fbm(76)[..., None]))
# fil de fer
fil = np.array([.16, .14, .12])*(.7+.6*noise(100, 77)[..., None]) + np.array([.15, .07, .02])*rust
# caisses : bois clair, planches
cw = .5+.5*np.sin(yy*2*np.pi*14 + 2*fbm(78)); caisse = np.array([.42, .33, .21])*(.7+.35*cw[..., None])*(1-.45*((yy*4) % 1 < .02)[..., None])
laiton = np.array([.55, .42, .18])*(.8+.3*fbm(79)[..., None])
TEX = {'Metal': png(metal), 'Chenille': png(chen), 'Kaki': png(kaki), 'Fil': png(fil), 'Caisse': png(caisse), 'Laiton': png(laiton),
       'Bois': ns['TEX']['Bois'], 'Sacs': ns['TEX']['Sacs'], 'Ecorce': an['TEX']['Ecorce'], 'Bois_eclate': an['TEX']['Bois_eclate']}

class M:
    def __init__(s): s.G = {}
    def g(s, m): return s.G.setdefault(m, ([], [], [], []))
    def poly(s, mat, V, n, U):
        Pm, Nm, Um, Im = s.g(mat); b = len(Pm); Pm.extend([tuple(v) for v in V]); Nm.extend([tuple(n)]*len(V)); Um.extend(U)
        for i in range(1, len(V)-1):
            t = [b, b+i, b+i+1]; A, B_, C = (np.array(V[k]) for k in (0, i, i+1))
            Im.extend(t if np.dot(np.cross(B_-A, C-A), n) >= 0 else [t[0], t[2], t[1]])
    def obox(s, mat, c, size, R=np.eye(3), uvs=1.0):
        h = np.array(size)/2; c = np.array(c, float); L = int(np.argmax(size)); off = rng.random(2)
        for ax in range(3):
            for sd in (-1, 1):
                o = [a for a in range(3) if a != ax]; ua = L if L in o else o[0]; va = o[1] if ua == o[0] else o[0]
                V, U = [], []
                for (p, q) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    lp = np.zeros(3); lp[ax] = sd*h[ax]; lp[o[0]] = p*h[o[0]]; lp[o[1]] = q*h[o[1]]
                    V.append(c+R @ lp); U.append((lp[ua]*uvs+off[0], lp[va]*uvs+off[1]))
                n = np.zeros(3); n[ax] = sd; s.poly(mat, V, R @ n, U)
    def beam(s, mat, a, b, w, h, roll=0.0, uvs=1.0):
        a, b = np.array(a, float), np.array(b, float); d = b-a; L = np.linalg.norm(d); d /= L
        s.obox(mat, (a+b)/2, (w, h, L), rotm(math.atan2(d[0], d[2]), -math.asin(np.clip(d[1], -1, 1)), roll), uvs)
    def cyl(s, mat, a, b, r, seg=12, caps=True, r2=None):
        a, b = np.array(a, float), np.array(b, float); d = b-a; L = np.linalg.norm(d); d /= L; r2 = r if r2 is None else r2
        ref = np.array([0, 1., 0]) if abs(d[1]) < .9 else np.array([1., 0, 0]); u = np.cross(d, ref); u /= np.linalg.norm(u); v = np.cross(d, u)
        for k in range(seg):
            a0, a1 = 2*math.pi*k/seg, 2*math.pi*(k+1)/seg; n0 = u*math.cos(a0)+v*math.sin(a0); n1 = u*math.cos(a1)+v*math.sin(a1)
            V = [a+n0*r, a+n1*r, b+n1*r2, b+n0*r2]
            Pm, Nm, Um, Im = s.g(mat); bb = len(Pm); Pm.extend([tuple(x) for x in V]); Nm.extend([tuple(n0), tuple(n1), tuple(n1), tuple(n0)])
            Um.extend([(k/seg*2, 0), ((k+1)/seg*2, 0), ((k+1)/seg*2, L), (k/seg*2, L)])
            t1 = [bb, bb+1, bb+2]; A, B_, C = V[0], V[1], V[2]
            Im.extend([bb, bb+1, bb+2, bb, bb+2, bb+3] if np.dot(np.cross(B_-A, C-A), n0+n1) > 0 else [bb, bb+2, bb+1, bb, bb+3, bb+2])
        if caps:
            for c, rr, n in ((a, r, -d), (b, r2, d)):
                s.poly(mat, [c+(u*math.cos(2*math.pi*k/seg)+v*math.sin(2*math.pi*k/seg))*rr for k in range(seg)], n,
                       [(.5+.5*math.cos(2*math.pi*k/seg), .5+.5*math.sin(2*math.pi*k/seg)) for k in range(seg)])
    def prism(s, mat_cap, mat_side, pts_zy, x0, x1, uvs=.5, side_uv=1.0):
        """polygone convexe (z, y) extrudé de x0 à x1"""
        cz = sum(p[0] for p in pts_zy)/len(pts_zy); cy = sum(p[1] for p in pts_zy)/len(pts_zy)
        for xc, nx in ((x0, -1.), (x1, 1.)):
            s.poly(mat_cap, [(xc, y, z) for z, y in pts_zy], (nx, 0, 0), [(z*uvs, y*uvs) for z, y in pts_zy])
        acc = 0.0
        for i in range(len(pts_zy)):
            (za, ya), (zb, yb) = pts_zy[i], pts_zy[(i+1) % len(pts_zy)]; L = math.hypot(zb-za, yb-ya); nz, ny = (yb-ya)/L, -(zb-za)/L
            if nz*((za+zb)/2-cz)+ny*((ya+yb)/2-cy) < 0: nz, ny = -nz, -ny
            s.poly(mat_side, [(x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za)], (0, ny, nz),
                   [(acc*side_uv, 0), ((acc+L)*side_uv, 0), ((acc+L)*side_uv, (x1-x0)), (acc*side_uv, (x1-x0))]); acc += L
    def sandbag(s, c, rot, L=.55, W=.32, H=.17):
        Pm, Nm, Um, Im = s.g('Sacs'); b0 = len(Pm); k = 10; cr, sr = math.cos(rot), math.sin(rot)
        ring = [(math.cos(2*math.pi*i/k)*W/2*(1-.12*abs(math.sin(2*math.pi*i/k))), math.sin(2*math.pi*i/k)*H/2) for i in range(k)]
        P = []
        for t in (-1, -.8, .8, 1):
            sc = .55 if abs(t) == 1 else 1.0
            for i, (a, bq) in enumerate(ring):
                lx, ly, lz = a*sc, bq*sc, t*L/2; P.append((c[0]+lx*cr+lz*sr, c[1]+ly, c[2]-lx*sr+lz*cr)); Um.append((i/k*1.4, (t+1)*.6))
        P.append((c[0]-L/2*sr, c[1], c[2]-L/2*cr)); Um.append((.5, .5)); P.append((c[0]+L/2*sr, c[1], c[2]+L/2*cr)); Um.append((.5, .5))
        T = []
        for j in range(3):
            for i in range(k): a, bb = j*k+i, j*k+(i+1) % k; T += [(a, bb, a+k), (bb, bb+k, a+k)]
        for i in range(k): T += [(4*k, (i+1) % k, i), (4*k+1, 3*k+i, 3*k+(i+1) % k)]
        P = np.array(P); T = np.array(T); cc = np.array(c); N = np.zeros_like(P)
        for t in T:
            fn = np.cross(P[t[1]]-P[t[0]], P[t[2]]-P[t[0]])
            if np.dot(fn, P[t].mean(0)-cc) < 0: t[1], t[2] = t[2], t[1]; fn = -fn
            N[t] += fn
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        Pm.extend(P.tolist()); Nm.extend(N.tolist()); Im.extend((T+b0).ravel().tolist())
    def merge_tree(s, t):
        for m, (Pm, Nm, Um, Im) in t.G.items():
            P2, N2, U2, I2 = s.g(m); b = len(P2); P2.extend(Pm); N2.extend(Nm); U2.extend(Um); I2.extend([i+b for i in Im])
    def transform(s, R, off):
        for m, (Pm, Nm, Um, Im) in s.G.items():
            P = np.array(Pm) @ R.T + off; N = np.array(Nm) @ R.T; Pm[:] = P.tolist(); Nm[:] = N.tolist()
    def write(s, path, name):
        for m, (Pm, Nm, Um, Im) in s.G.items():               # triangles dans le sens de leurs normales
            P = np.array(Pm); N = np.array(Nm); I = np.array(Im).reshape(-1, 3)
            fn = np.cross(P[I[:, 1]]-P[I[:, 0]], P[I[:, 2]]-P[I[:, 0]]); bad = (fn*N[I].sum(1)).sum(1) < 0; I[bad] = I[bad][:, [0, 2, 1]]; Im[:] = I.ravel().tolist()
        src = "class _W:\n" + open(D+'make_meubles.py').read().split("class Mesh:\n")[1].split("\nD = '")[0]
        src = src.replace("'roughnessFactor': .85 if m == 'Bois' else .95", "'roughnessFactor': {'Metal': .7, 'Laiton': .45}.get(m, .92)")
        g = dict(globals()); exec(src, g); w = g['_W'](); w.G = {k: v for k, v in s.G.items() if v[3]}; w.write(path, name)
def rotm(yaw=0, pitch=0, roll=0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    return np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])

# ======================= épave de char (rhomboïde, 8 m), piquée dans le sol
t = M()
side = [(-2.8, 0), (2.6, 0), (4.0, 1.1), (3.75, 2.25), (3.2, 2.45), (-3.4, 2.45), (-4.0, 1.6), (-3.95, .9)]
for sx in (-1, 1):
    t.prism('Metal', 'Chenille', side, *sorted((sx*1.35, sx*2.0)), side_uv=.5)
t.obox('Metal', (0, 1.3, -.3), (2.7, 1.6, 5.0), uvs=.5)
t.obox('Metal', (0, 2.35, 1.75), (1.5, .55, 1.0), uvs=.5)                                       # cabine
t.obox('Metal', (0, 2.25, -1.6), (1.2, .35, 1.2), uvs=.5)                                       # trappe arrière
for sx in (-1, 1):
    t.obox('Metal', (sx*2.35, 1.35, .3), (.7, 1.0, 1.8), uvs=.5)                               # tourelles latérales
    t.obox('Metal', (sx*2.2, 1.35, 1.25), (.5, .7, .25), uvs=.5)
    if sx < 0: t.cyl('Metal', (sx*2.25, 1.45, 1.35), (sx*2.25, 1.45, 2.6), .055, 10)
    else: t.cyl('Metal', (sx*2.25, 1.45, 1.35), (sx*2.6, 1.1, 2.3), .055, 10)                 # canon tordu
t.beam('Bois', (-2.1, 2.62, -2.6), (2.1, 2.62, -2.6), .3, .3)                                 # poutre de déblocage
for k in range(5):                                                                              # morceaux de tôle arrachés
    t.obox('Metal', (rng.uniform(-3, 3), .15+rng.uniform(0, .2), rng.uniform(-4.8, -3.6)), (rng.uniform(.4, .9), .03, rng.uniform(.3, .7)),
           rotm(rng.uniform(0, 6.3), rng.normal(0, .4), rng.normal(0, .4)), .5)
for k in range(7):                                                                              # chenille déroulée
    t.obox('Chenille', (2.6+k*.05, .05, -3.0-k*.32), (.62, .07, .3), rotm(.2, 0, rng.normal(0, .05)), 1)
t.transform(rotm(0, math.radians(7), math.radians(5)), np.array([0, -.35, 0]))                  # piqué dans un trou, penché
t.write(D+'fr_char.glb', 'Char')

# ======================= canon de campagne abandonné (bouclier, fût, flèche)
c = M()
def wheel(cx, cy, cz, r=.7):
    for k in range(16):
        a0, a1 = 2*math.pi*k/16, 2*math.pi*(k+1)/16
        c.beam('Bois', (cx, cy+r*math.cos(a0), cz+r*math.sin(a0)), (cx, cy+r*math.cos(a1), cz+r*math.sin(a1)), .1, .08)
    for k in range(12):
        a = 2*math.pi*k/12; c.beam('Bois', (cx, cy, cz), (cx, cy+.66*math.cos(a), cz+.66*math.sin(a)), .045, .045)
    c.cyl('Metal', (cx-.09, cy, cz), (cx+.09, cy, cz), .1, 10)
wheel(-.85, .7, 0); wheel(.85, .7, 0)
c.cyl('Metal', (-.95, .7, 0), (.95, .7, 0), .045, 8)
c.obox('Kaki', (0, .95, .2), (1.55, 1.1, .03), rotm(0, math.radians(-10), 0), .7)               # bouclier
c.obox('Kaki', (0, 1.55, .25), (.9, .2, .025), rotm(0, math.radians(20), 0), .7)
c.cyl('Kaki', (0, 1.0, -.6), (0, 1.07, 2.25), .065, 12, True, .055)                              # fût
c.cyl('Kaki', (0, .86, -.7), (0, .9, 1.1), .1, 10)                                               # frein
c.beam('Kaki', (0, .8, -.4), (0, .08, -3.1), .2, .16)                                            # flèche
c.obox('Metal', (0, .15, -3.15), (.55, .35, .05), rotm(0, math.radians(-30), 0), .7)              # bêche
for k in range(6):                                                                                # douilles d'obus éparses
    x, z, a = rng.uniform(-1.5, 1.5), rng.uniform(-2.4, -.4), rng.uniform(0, 6.3)
    c.cyl('Laiton', (x, .045, z), (x+.38*math.cos(a), .045, z+.38*math.sin(a)), .043, 10)
c.transform(rotm(0, 0, math.radians(-9)), np.array([0, -.08, 0]))                                 # une roue enfoncée
c.write(D+'fr_canon.glb', 'Canon')

# ======================= nid de sacs de sable (arc ouvert vers l'arrière, -Z)
n = M()
for layer in range(8):                                    # muret de 1,25 m : couvre un tireur accroupi
    r = 1.6-layer*.035; y = .085+layer*.15; a0 = -110+(layer % 2)*9
    for a in np.arange(a0, 111, 18 if layer < 7 else 24):
        ar = math.radians(a); n.sandbag((r*math.sin(ar), y, r*math.cos(ar)), ar+math.pi/2+rng.normal(0, .06))
for k in range(5): n.sandbag((rng.uniform(-1.2, 1.2), .085, rng.uniform(-1.6, -.9)), rng.uniform(0, 6.3))
n.obox('Caisse', (.6, .17, -.4), (.62, .34, .38), rotm(.4), 1.4)
n.write(D+'fr_nid.glb', 'NidSacs')

# ======================= tronc abattu (5 m), bouts éclatés
n2 = M()                                                  # pile de trois rondins (1,1 m)
for k, (oz, oy, ox, L, r0) in enumerate(((-.33, .32, 0, 5.2, .34), (.34, .31, .15, 4.7, .32), (0, .86, -.2, 4.4, .3))):
    tr = an['Tree'](55+k); pts = [np.array([ox-L/2+L*i/12, oy+.04*math.sin(i*.9+k), oz+.05*math.sin(i*1.3+k)]) for i in range(13)]
    tr.tube(pts, [r0-.06*i/12 for i in range(13)], seg=11, lobes=.06)
    for end, d in ((pts[0], np.array([-1., 0, 0])), (pts[-1], np.array([1., 0, 0]))):
        tr.splinters(end, d, (np.array([0, 1., 0]), np.array([0, 0, 1.])), r0*.85, count=6)
    if k == 2: tr.branch(pts[6], (.2, .8, .4), 1.0, .06, 0, broken_p=1.0)
    tr.fix_winding(); n2.merge_tree(tr)
n2.write(D+'fr_tronc.glb', 'Tronc')

# ======================= cheval de frise (3 m) avec barbelés
f = M(); Lf = 3.0
f.beam('Bois', (-Lf/2, .62, 0), (Lf/2, .62, 0), .12, .12)
tips = []
for x in np.arange(-Lf/2+.25, Lf/2-.2, .62):
    for sg in (-1, 1):
        a, b = np.array([x, .62-.78, -sg*.78]), np.array([x, .62+.78, sg*.78])
        f.beam('Bois', a, b, .07, .07, rng.normal(0, .1)); tips += [a, b]
    tips.append(None)
ends = [p for p in tips if p is not None]
groups = [ends[i::4] for i in range(4)]
for gp in groups:                                                                                # 4 fils le long, plus des fils en zigzag
    for p, q in zip(gp[:-1], gp[1:]): f.beam('Fil', p+[0, -.05, 0], q+[0, -.05, 0], .012, .012)
for i in range(len(groups[0])-1):
    f.beam('Fil', groups[1][i], groups[2][i+1], .01, .01); f.beam('Fil', groups[3][i], groups[0][i+1], .01, .01)
f.write(D+'fr_frise.glb', 'ChevalDeFrise')

# ======================= pile de caisses de munitions (+ obus renversés)
p = M()
spots = [(0, 0, 0, 0), (.66, 0, .05, .08), (-.64, 0, -.02, -.05), (.0, 0, .45, .1), (.32, .34, .02, .2), (-.33, .34, .05, -.1), (0, .68, .1, .35), (.66, 0, .5, -.3)]
for x, y, z, a in spots:
    R = rotm(a); p.obox('Caisse', (x, y+.17, z), (.62, .34, .38), R, 1.4)
    for sg in (-1, 1): p.obox('Metal', np.array([x, y+.24, z])+R @ np.array([sg*.31, 0, 0]), (.015, .04, .12), R)   # poignées
for k in range(5):
    a = rng.uniform(0, 6.3); x, z = 1.0+rng.uniform(0, .5), rng.uniform(-.6, .6)
    p.cyl('Laiton', (x, .06, z), (x+.3*math.cos(a), .06, z+.3*math.sin(a)), .06, 10)
    p.cyl('Metal', (x+.3*math.cos(a), .06, z+.3*math.sin(a)), (x+.42*math.cos(a), .06, z+.42*math.sin(a)), .055, 10, True, .02)
p.write(D+'fr_caisses.glb', 'Caisses')
