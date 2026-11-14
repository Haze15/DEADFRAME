"""Carte « Front » pour DEADFRAME : assemble les modèles (tranchées, rampes, ruines, arbres morts, sol boueux),
fabrique le sol de la carte, la carte des hauteurs (collisions) et les données JS. Sorties : assets/fr_*.dfm, assets/fr_hf.bin, front.json"""
import sys, os, json, struct, math, io, numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, 'tools'); import convert
OUT = 'tools/modeles'; ASSETS = 'assets'
DEPTH = 2.0; SURF = DEPTH+.05

# ======================= 1. pièces de tranchée pour la carte
ns = {}
src = open('tools/modeles/make_trench.py').read().split("\nD = '")[0]
src = src.replace("jy = (rng.normal(0, .07) if abs(px) > 1.0 else", "jy = (rng.normal(0, .07) if 1.0 < abs(px) < 2.6 else")   # bords latéraux à plat
exec(src, ns)
ns['build']([(0, 4), (0, -4)], OUT+'/fr_droite.glb')
RAMP = r'''
def build_ramp(out, mirror=False):
    """sortie de tranchée : le fond remonte de 0 (entrée z=+4) au niveau du sol (z=-4), les parois s'effacent"""
    global G, rng
    rng = np.random.default_rng(15 if not mirror else 16); G = {k: ([], [], [], []) for k in TEX}
    def ramp(t):
        u = min(1.0, max(0.0, (t-.8)/6.8)); return SURF*u*u*(3-2*u)
    prof = [(-px, py) for px, py in reversed(PROF)] if mirror else PROF
    arc = np.concatenate([[0], np.cumsum([math.dist(prof[i], prof[i+1]) for i in range(len(prof)-1)])])
    P, UV = [], []; zs = np.linspace(4, -4, 33)
    for z in zs:
        t = 4-z; r = ramp(t); f = r/SURF; env = math.sin(math.pi*t/8)
        for k, (px, py) in enumerate(prof):
            y = max(py, r) if abs(px) <= .9 else py+(SURF-py)*f
            jy = (rng.normal(0, .07) if 1.0 < abs(px) < 2.6 else rng.normal(0, .02) if y < .06+r and abs(px) < .9 else 0)*env
            P.append((px, y+jy, z)); UV.append((arc[k]*.5, -t*.5))
    I = []; M = len(prof)
    for i in range(len(zs)-1):
        for k in range(M-1):
            a, b = i*M+k, i*M+k+1; c, d = a+M, b+M; I += [a, b, c, b, d, c]
    tri_mesh('Terre', P, UV, I)
    for s in (-1, 1):                                            # coffrage : seulement au-dessus de la rampe
        for i in range(8):
            rmax = ramp(i+1)
            for row in range(8):
                yc = .14+row*.225+rng.normal(0, .008)
                if yc-.1 >= rmax-.02: box('Bois', (s*(HALF_W+.035), yc, 3.5-i), (.035, .2, .99), .9, rng.normal(0, .004))
        for t in (0.06, 2, 4):
            r = ramp(t); h = 1.95+rng.uniform(0, .1)-r
            if h > .35: box('Bois', (s*(HALF_W-.02), r+h/2, 4-t), (.12, h, .12), .8, rng.normal(0, .03))
    for s in (-1, 1): box('Bois', (s*.3, .05, 3.5), (.07, .09, .98), 1.2)
    for k in range(6): box('Bois', (rng.normal(0, .01), .115, 3.92-k*.168), (.92, .04, .1), 1.2, rng.normal(0, .025))
    sg = 1 if mirror else -1
    for layer in range(3):
        t = .29+(.29 if layer % 2 else 0)
        while t < 7.7:
            sandbag((sg*(1.02-layer*.04)+rng.normal(0, .02), DEPTH+.07+layer*.155+(SURF-DEPTH)*ramp(t)/SURF, 4-t), rot=math.pi/2+rng.normal(0, .06)); t += .58
    write_glb(out)
'''
ns['SURF'] = SURF; exec(RAMP, ns)
ns['build_ramp'](OUT+'/fr_rampe.glb'); ns['build_ramp'](OUT+'/fr_rampe_m.glb', mirror=True)
nsx = {}
srcx = open('tools/modeles/make_intersection.py').read().split("\nD = '")[0]
exec(srcx, nsx)
nsx['build_x']('W', OUT+'/fr_T.glb'); nsx['build_x']('EW', OUT+'/fr_X.glb')

# ======================= 2. disposition (centres sur une grille de 8 m ; rotation en degrés, comme M.ry du jeu)
north = [('fr_rampe_m', -32, 24, 90), ('fr_droite', -24, 24, -90), ('fr_T', -16, 24, -90), ('fr_rampe', -16, 16, 0),
         ('fr_droite', -8, 24, -90), ('fr_X', 0, 24, -90), ('fr_rampe_m', 0, 32, 180), ('fr_rampe', 0, 16, 0),
         ('fr_droite', 8, 24, -90), ('fr_T', 16, 24, -90), ('fr_rampe', 16, 16, 0), ('fr_droite', 24, 24, -90), ('fr_rampe', 32, 24, -90)]
TILES = north + [(m, -x, -z, d+180) for m, x, z, d in north]
RUINS = [(-22.0, 4.0, 0), (22.0, -3.0, 180)]
TREES = [('fr_arbre1', -31, -8, 40), ('fr_arbre2', -6, 9, 200), ('fr_arbre3', 7, -10, 10), ('fr_arbre2', 31, 9, 90), ('fr_arbre4', -35, 34, 300),
         ('fr_arbre1', 13, 35, 120), ('fr_arbre3', 35, -35, 60), ('fr_arbre4', -13, -35, 150), ('fr_arbre3', -2, -2, 250), ('fr_arbre1', 9, 4, 330),
         ('fr_arbre2', -30, -35, 20), ('fr_arbre3', 26, 36, 270)]
# couverts du no man's land : (modèle, x, z, rotation en degrés, rayon d'emprise)
COVERS = [('fr_char', -9.0, 1.0, -35, 5.0), ('fr_canon', 12.0, -11.0, 160, 3.0), ('fr_canon', -27.0, -12.0, 20, 3.0),
          ('fr_nid', -31.0, 12.0, 190, 2.2), ('fr_nid', -5.0, 13.0, 170, 2.2), ('fr_nid', 25.0, 12.0, 160, 2.2),
          ('fr_nid', 30.0, -12.0, 10, 2.2), ('fr_nid', 4.0, -13.0, 0, 2.2), ('fr_nid', -19.0, -14.0, 350, 2.2),
          ('fr_tronc', 17.0, 8.0, 70, 3.0), ('fr_tronc', -15.0, -6.0, 20, 3.0), ('fr_tronc', 1.0, 8.5, 100, 3.0), ('fr_tronc', -35.0, -1.0, 85, 3.0),
          ('fr_frise', -25.0, 16.0, 0, 1.8), ('fr_frise', -9.0, 15.5, 10, 1.8), ('fr_frise', 8.0, 16.0, -8, 1.8), ('fr_frise', 26.0, 16.5, 5, 1.8),
          ('fr_frise', -26.0, -16.5, 175, 1.8), ('fr_frise', -8.0, -16.0, 185, 1.8), ('fr_frise', 9.0, -15.5, 172, 1.8), ('fr_frise', 25.0, -16.0, 180, 1.8),
          ('fr_caisses', -12.0, 11.0, 40, 1.6), ('fr_caisses', 11.0, -2.0, 15, 1.6)]
def rot2(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def glb_tris(fn, mats=None):
    d = open(fn, 'rb').read(); jl = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20+jl]); B = d[20+jl+8:]
    def A(i):
        a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}[a['componentType']]
        r = np.frombuffer(B, dt, a['count']*n, v['byteOffset']); return r.reshape(-1, n) if n > 1 else r
    out = []
    for pr in j['meshes'][0]['primitives']:
        nm = j['materials'][pr['material']]['name']
        if mats and nm not in mats: continue
        P = A(pr['attributes']['POSITION']).astype(float); I = A(pr['indices']).reshape(-1, 3)
        out.append(P[I])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))
def place(T, x, y, z, deg): return T @ rot2(deg).T + np.array([x, y, z])

# ======================= 3. couverture des tranchées (pour trouer le sol) et rastériseur
def raster(grid, x0, st, tris, cover=None, mode='max'):
    n = grid.shape[0]
    for t in tris:
        xs, zs = t[:, 0], t[:, 2]
        i0 = max(0, int(math.ceil((xs.min()-x0)/st))); i1 = min(n-1, int(math.floor((xs.max()-x0)/st)))
        j0 = max(0, int(math.ceil((zs.min()-x0)/st))); j1 = min(n-1, int(math.floor((zs.max()-x0)/st)))
        if i1 < i0 or j1 < j0: continue
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        den = (bz-cz)*(ax-cx)+(cx-bx)*(az-cz)
        if abs(den) < 1e-10: continue
        X, Z = np.meshgrid(x0+st*np.arange(i0, i1+1), x0+st*np.arange(j0, j1+1))
        w0 = ((bz-cz)*(X-cx)+(cx-bx)*(Z-cz))/den; w1 = ((cz-az)*(X-cx)+(ax-cx)*(Z-cz))/den; w2 = 1-w0-w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        h = w0*ay+w1*by+w2*cy
        sub = grid[j0:j1+1, i0:i1+1]; sub[m] = np.maximum(sub[m], h[m])
        if cover is not None: cover[j0:j1+1, i0:i1+1] |= m
tile_terre = {}; tile_all = {}
for nm in ('fr_droite', 'fr_rampe', 'fr_rampe_m', 'fr_T', 'fr_X'):
    tile_terre[nm] = glb_tris(f'{OUT}/{nm}.glb', {'Terre'}); tile_all[nm] = glb_tris(f'{OUT}/{nm}.glb', {'Terre', 'Sacs'})
CX0, CST = -42.0, .5; CN = int(84/CST)+1
cov = np.zeros((CN, CN), bool); tmp = np.full((CN, CN), -99.0)
for m, x, z, d in TILES: raster(tmp, CX0, CST, place(tile_terre[m], x, 0, z, d), cov)
dist_tr = ndimage.distance_transform_edt(~cov)*CST

# ======================= 4. sol de la carte (relief, cratères, flaques) + texture unique
rng = np.random.default_rng(1918)
gx = CX0+CST*np.arange(CN); GX, GZ = np.meshgrid(gx, gx)
def smooth_field(cells, seed, amp, size=84.0):
    g = np.random.default_rng(seed).random((cells, cells)).astype(np.float32)
    a = np.asarray(Image.fromarray(g, 'F').resize((CN, CN), Image.BICUBIC), float); return amp*(a-.5)
und = smooth_field(9, 5, .5)+smooth_field(21, 6, .18)
dist_ruin = np.full((CN, CN), 99.0)
for rx, rz, _ in RUINS: dist_ruin = np.minimum(dist_ruin, np.maximum(np.abs(GX-rx)-4.4, np.abs(GZ-rz)-3.4).clip(0))
for _, cx_, cz_, _, cr_ in COVERS: dist_ruin = np.minimum(dist_ruin, (np.hypot(GX-cx_, GZ-cz_)-cr_*.8).clip(0))
craters = []
for _ in range(3000):
    R = rng.choice([1.4, 1.9, 2.5, 3.2, 4.0], p=[.28, .28, .22, .14, .08]); x, z = rng.uniform(-38, 38, 2)
    i, j = int(round((x-CX0)/CST)), int(round((z-CX0)/CST))
    if dist_tr[j, i] < R+2.2 or dist_ruin[j, i] < R+4.5 or any(math.hypot(x-tx, z-tz) < R+1.2 for _, tx, tz, _ in TREES): continue
    if all(math.hypot(x-cx, z-cz) > (R+cr)*.8 for cx, cz, cr, _ in craters): craters.append((x, z, R, R*rng.uniform(.3, .4)))
    if len(craters) >= 34: break
def crater_field(X, Z):
    c = np.zeros_like(X)
    for cx, cz, R, d in craters:
        r = np.hypot(X-cx, Z-cz)/R; c += -d*np.clip(1-r*r, 0, None)**1.3 + .3*d*np.exp(-((r-1.05)/.32)**2)
    return c
ss = lambda a, b, v: np.clip((v-a)/(b-a), 0, 1)**2*(3-2*np.clip((v-a)/(b-a), 0, 1))
edge = ss(42, 37, np.maximum(np.abs(GX), np.abs(GZ)))
mask = ss(1.0, 3.5, dist_tr)*ss(.5, 3.0, dist_ruin)*edge
CF = crater_field(GX, GZ)
GH = SURF + (und+CF)*mask - .05*(1-ss(0, 1.5, dist_tr)) - .02*(dist_ruin < .5)
GH = np.where(cov, tmp, GH)                                        # bord du sol collé exactement au bord des tuiles (pas de fente)
# trous : cellules entièrement couvertes par une tranchée
skip = cov[:-1, :-1] & cov[1:, :-1] & cov[:-1, 1:] & cov[1:, 1:]
dzx = np.gradient(GH, CST, axis=1); dzz = np.gradient(GH, CST, axis=0)
NRM = np.stack([-dzx, np.ones_like(GH), -dzz], -1); NRM /= np.linalg.norm(NRM, axis=-1, keepdims=True)
# texture unique 2048 (même recette que terrain_boue.glb)
tsrc = open('tools/modeles/make_terrain.py').read()
tns = {}; exec(tsrc.split("# ---------------- relief")[0], tns)
terre, boue = tns['terre'], tns['boue']
TS = 2048; px = (np.arange(TS)+.5)/TS*84-42; PX, PZ = np.meshgrid(px, px); rep = TS//21
def tiled(arr):
    t = np.asarray(Image.fromarray((np.clip(arr, 0, 1)*255).astype(np.uint8)).resize((rep, rep), Image.LANCZOS), float)/255
    return np.tile(t, (TS//rep+1, TS//rep+1, 1))[:TS, :TS]
cfp = crater_field(PX, PZ)
mk = np.asarray(Image.fromarray((mask*255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float)/255
dtr = np.asarray(Image.fromarray(np.clip(dist_tr*20, 0, 255).astype(np.uint8)).resize((TS, TS), Image.BILINEAR), float)/20
blot = np.asarray(Image.fromarray((np.random.default_rng(7).random((40, 40))*255).astype(np.uint8)).resize((TS, TS), Image.BICUBIC), float)/255
fine = np.asarray(Image.fromarray((np.random.default_rng(8).random((180, 180))*255).astype(np.uint8)).resize((TS, TS), Image.BICUBIC), float)/255
wet = np.clip((-cfp*mk-.12)/.35 + (blot-.66)*3.0 + (fine-.5)*.8 + .5*(1-ss(0, 2.5, dtr)), 0, 1)
col = tiled(terre)*(1-wet[..., None]) + tiled(boue)*wet[..., None]
col = col*(1+.14*np.clip(cfp*mk/.25, 0, 1)[..., None])*np.clip(1+cfp*mk*.35, .55, 1)[..., None]
TEXS = {}
b = io.BytesIO(); Image.fromarray((np.clip(col, 0, 1)*255).astype(np.uint8)).save(b, 'JPEG', quality=90); TEXS['Sol'] = b.getvalue()
for k in ('Terre', 'Eau'): TEXS[k] = tns['TEX'][k]
G = {}
def g(m): return G.setdefault(m, ([], [], [], []))
Pm, Nm, Um, Im = g('Sol')
for j in range(CN):
    for i in range(CN): Pm.append((GX[j, i], GH[j, i], GZ[j, i])); Nm.append(tuple(NRM[j, i])); Um.append(((GX[j, i]+42)/84, (GZ[j, i]+42)/84))
for j in range(CN-1):
    for i in range(CN-1):
        if skip[j, i]: continue
        a, b_, c, d = j*CN+i, j*CN+i+1, (j+1)*CN+i, (j+1)*CN+i+1; Im.extend([a, c, b_, b_, c, d])
# bordure (au-delà de 42 m, pour l'horizon) : maillage grossier, texture répétée
Pm, Nm, Um, Im = g('Terre'); o = np.arange(-72, 72.1, 2.0); n_ = len(o)
for zz in o:
    for xx in o:
        e = max(abs(xx), abs(zz)); y = SURF-.02 + (0 if e <= 44 else .4*math.sin(xx*.11)*math.sin(zz*.13))
        Pm.append((xx, y, zz)); Nm.append((0, 1, 0)); Um.append((xx*.25, zz*.25))
for j in range(n_-1):
    for i in range(n_-1):
        if max(abs(o[i]), abs(o[i+1])) <= 42 and max(abs(o[j]), abs(o[j+1])) <= 42: continue
        a, b_, c, d = j*n_+i, j*n_+i+1, (j+1)*n_+i, (j+1)*n_+i+1; Im.extend([a, c, b_, b_, c, d])
# flaques
for cx, cz, R, d in craters:
    if R < 2.4: continue
    i, j = int(round((cx-CX0)/CST)), int(round((cz-CX0)/CST)); level = GH[j, i] + .3*d*mask[j, i]
    if mask[j, i] < .9: continue
    Pm, Nm, Um, Im = g('Eau'); b0 = len(Pm); k = 26; rw = R*.6
    Pm.append((cx, level, cz)); Nm.append((0, 1, 0)); Um.append((cx*.2, cz*.2))
    for t in range(k):
        a = 2*math.pi*t/k; rr = rw*(1+.08*math.sin(3*a+cx)); Pm.append((cx+rr*math.cos(a), level, cz+rr*math.sin(a))); Nm.append((0, 1, 0)); Um.append(((cx+rr*math.cos(a))*.2, (cz+rr*math.sin(a))*.2))
    for t in range(k): Im.extend([b0, b0+1+(t+1) % k, b0+1+t])
_src = "class _M:\n" + open('tools/modeles/make_meubles.py').read().split("class Mesh:\n")[1].split("\nD = '")[0]
_src = _src.replace("I = np.array(Im, np.uint16)", "I = np.array(Im, np.uint32 if len(P) > 65535 else np.uint16)")
_src = _src.replace("'indices': acc(I, 'SCALAR', 5123, 34963)", "'indices': acc(I, 'SCALAR', 5125 if I.dtype == np.uint32 else 5123, 34963)")
_src = _src.replace("'mimeType': 'image/png'", "'mimeType': 'image/jpeg' if TEX[m][:2] == bytes([255, 216]) else 'image/png'")
TEX = TEXS; exec(_src)
mm_ = _M(); mm_.G = {k: v for k, v in G.items() if v[3]}; mm_.write(OUT+'/fr_sol.glb', 'Sol')
gh = lambda x, z: float(ndimage.map_coordinates(GH, [[(z-CX0)/CST], [(x-CX0)/CST]], order=1)[0])

# ======================= 5. ruines (+ boîtes de collision des murs) et arbres (+ troncs)
rns = {'__name__': 'ruine'}
rsrc = open('tools/modeles/make_ruine.py').read()
rsrc = rsrc.replace('def wbox(mat, x0, y0, z0, x1, y1, z1, uvs=.5):\n', "def wbox(mat, x0, y0, z0, x1, y1, z1, uvs=.5):\n    if mat == 'Pierre': COLL.append((x0, y0, z0, x1, y1, z1))\n")
rsrc = rsrc.replace("'tools/modeles/maison_detruite.glb'", "'%s/fr_ruine.glb'" % OUT)
rns['COLL'] = []; exec(rsrc, rns)
def merge(bx):
    groups = {}
    for b in bx: groups.setdefault(tuple(round(v, 3) for v in (b[0], b[2], b[3], b[5])), []).append((b[1], b[4]))
    out = []
    for (x0, z0, x1, z1), ys in groups.items():
        ys.sort(); cur = list(ys[0])
        for y0, y1 in ys[1:]:
            if y0 <= cur[1]+1e-4: cur[1] = max(cur[1], y1)
            else: out.append((x0, cur[0], z0, x1, cur[1], z1)); cur = [y0, y1]
        out.append((x0, cur[0], z0, x1, cur[1], z1))
    return out
ruin_boxes = merge(rns['COLL'])
BOXES = []
for rx, rz, deg in RUINS:
    for x0, y0, z0, x1, y1, z1 in ruin_boxes:
        if deg == 180: x0, x1, z0, z1 = -x1, -x0, -z1, -z0
        BOXES.append([round(v, 3) for v in (x0+rx, y0+SURF, z0+rz, x1+rx, y1+SURF, z1+rz)])
ans = {}; asrc = open('tools/modeles/make_arbres.py').read()
asrc = asrc.replace("        return pts, radii", "        s.tp = pts; s.tr = radii\n        return pts, radii")
asrc = asrc.replace("\nD = 'tools/modeles/'", "\nTree.write = lambda s, path, name: TREEOBJ.__setitem__(name, s)\nD = 'tools/modeles/'")
ans['TREEOBJ'] = {}; exec(asrc, ans)
tmap = {'fr_arbre%d' % i: ans['TREEOBJ']['ArbreMort%d' % i] for i in range(1, 5)}
TREEPL = []
for nm, x, z, deg in TREES:
    y = gh(x, z); TREEPL.append((nm, x, y, z, deg)); t = tmap[nm]; R = rot2(deg)
    pts = [R @ p for p in t.tp]; rad = t.tr; seg = []
    for p, r in zip(pts, rad):
        if p[1] > 3.6: break
        seg.append((p, r))
    for k in range(0, len(seg)-1, 2):
        ch = seg[k:k+3]; ps = np.array([c[0] for c in ch]); r = max(c[1] for c in ch)*.85
        mn = ps.min(0)-[r, 0, r]; mx = ps.max(0)+[r, 0, r]
        BOXES.append([round(v, 3) for v in (mn[0]+x, max(mn[1], 0)+y-.1, mn[2]+z, mx[0]+x, mx[1]+y, mx[2]+z)])
for s in (-1, 1):                                                   # limites de la carte
    BOXES.append([-41.5, -1, s*41-.5 if s > 0 else -41.5, 41.5, 8, 41.5 if s > 0 else -40.5])
    BOXES.append([s*41-.5 if s > 0 else -41.5, -1, -41.5, 41.5 if s > 0 else -40.5, 8, 41.5])

# ======================= 6. carte des hauteurs (collisions) : 0,125 m sur [-44, 44]
HX0, HST = -44.0, .125; HN = int(88/HST)+1
H = np.full((HN, HN), -5.0)
raster(H, HX0, HST, np.concatenate([glb_tris(OUT+'/fr_sol.glb', {'Sol', 'Terre'})]))
for m, x, z, d in TILES: raster(H, HX0, HST, place(tile_all[m], x, 0, z, d))
rub = glb_tris(OUT+'/fr_ruine.glb', {'Gravats'})
for rx, rz, deg in RUINS: raster(H, HX0, HST, place(rub, rx, SURF, rz, deg))
COVPL = []
for nm, x, z, deg, r in COVERS:
    y = min(gh(x+dx, z+dz) for dx in (-r*.5, 0, r*.5) for dz in (-r*.5, 0, r*.5)) - .03; COVPL.append((nm, x, y, z, deg))
    raster(H, HX0, HST, place(glb_tris(f'{OUT}/{nm}.glb'), x, y, z, deg))
H[H < -4] = SURF
H = np.maximum(H, np.where(H < .12, .12, H))                       # caillebotis : on marche à 12 cm
q = np.clip(np.round((H+10)*200), 0, 65535).astype(np.uint16)
open(ASSETS+'/fr_hf.bin', 'wb').write(struct.pack('<4f2I', HX0, HX0, HST, float(H.max()), HN, HN) + q.tobytes())
np.save(OUT+'/hf.npy', H)

# ======================= 7. modèles -> .dfm, données JS
for nm, tex in (('fr_sol', 2048), ('fr_droite', 512), ('fr_rampe', 512), ('fr_rampe_m', 512), ('fr_T', 512), ('fr_X', 512), ('fr_ruine', 512)):
    convert.convert_static(f'{OUT}/{nm}.glb', nm, ASSETS, 10**7, tex=tex)
for nm in sorted(set(c[0] for c in COVERS)): convert.convert_static(f'{OUT}/{nm}.glb', nm, ASSETS, 10**7, tex=512)
for i in range(1, 5): convert.convert_static(f'tools/modeles/arbre_mort_{i}.glb', f'fr_arbre{i}', ASSETS, 10**7, tex=512)
props = [{'m': 'fr_sol', 'p': [0, 0, 0], 'r': 0}]
props += [{'m': m, 'p': [x, 0, z], 'r': round(math.radians(d), 5)} for m, x, z, d in TILES]
props += [{'m': 'fr_ruine', 'p': [rx, SURF, rz], 'r': round(math.radians(d), 5)} for rx, rz, d in RUINS]
props += [{'m': nm, 'p': [x, round(y-.05, 3), z], 'r': round(math.radians(d), 5)} for nm, x, y, z, d in TREEPL]
props += [{'m': nm, 'p': [x, round(y, 3), z], 'r': round(math.radians(d), 5)} for nm, x, y, z, d in COVPL]
lights = []
for sgn in (1, -1):
    for x in (-28, -20, -12, -4, 4, 12, 20, 28):
        lights.append([x*sgn, 1.75, sgn*(24+.5), 7.5])                # lanternes sur la paroi arrière
for rx, rz, _ in RUINS: lights.append([rx-2.2 if rx < 0 else rx+2.2, SURF+.5, rz+(-1 if rx < 0 else 1), 9])   # feu dans les ruines
spawns = [[-24, 24], [-8, 24], [8, 24], [24, 24], [0, 30], [24, -24], [8, -24], [-8, -24], [-24, -24], [0, -30],
          [-34, 4], [34, -4], [-12, -4], [12, 6], [-26, -14], [26, 14], [0, 10], [0, -10]]
json.dump({'props': props, 'boxes': BOXES, 'lights': lights, 'spawns': spawns, 'craters': len(craters)}, open(OUT+'/front.json', 'w'))
print('tuiles', len(TILES), 'boîtes', len(BOXES), 'cratères', len(craters), 'hauteurs', H.min().round(2), H.max().round(2))

# ======================= 8. données de la carte dans src/game.html (ligne « const FRONT=…; »)
import re
gp = 'src/game.html'; gs = open(gp, encoding='utf-8').read()
data = json.dumps({k: json.load(open(OUT+'/front.json'))[k] for k in ('props', 'boxes', 'lights', 'spawns')}, separators=(',', ':'))
gs2 = re.sub(r'const FRONT=\{.*?\};\n', lambda m: 'const FRONT=' + data + ';\n', gs, count=1, flags=re.S)
assets_js = "const FR_ASSETS=" + json.dumps(sorted(set(p['m'] for p in props)), separators=(',', ':')) + ";"
gs2 = re.sub(r'const FR_ASSETS=\[.*?\];', lambda m: assets_js, gs2, count=1)
if gs2 != gs: open(gp, 'w', encoding='utf-8').write(gs2); print('src/game.html : données FRONT mises à jour')
else: print('src/game.html : données FRONT déjà à jour')
