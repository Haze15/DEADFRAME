"""Maison détruite (village 14-18) -> maison_detruite.glb
Origine au sol au centre de la maison, Y en haut, mètres. Façade (porte) côté +Z. Emprise des murs : 8,4 x 6,4 m."""
import json, struct, io, math, numpy as np
from PIL import Image
rng = np.random.default_rng(1916)
S = 512
def png(a):
    b = io.BytesIO(); Image.fromarray((np.clip(a, 0, 1)*255).astype(np.uint8)).save(b, 'PNG', optimize=True); return b.getvalue()
def noise(cells, seed):
    g = np.tile(np.random.default_rng(seed).random((cells, cells)), (3, 3))
    return np.asarray(Image.fromarray((g*255).astype(np.uint8)).resize((S*3, S*3), Image.BICUBIC), float)[S:2*S, S:2*S]/255
def fbm(seed): return sum(noise(c, seed+i)*a for i, (c, a) in enumerate([(4, .5), (8, .25), (16, .13), (32, .07), (64, .05)]))
Y, X = np.mgrid[0:S, 0:S]

# ---------------- textures
def stone_tex():                                            # moellons assisés, 2 m x 2 m
    img = np.zeros((S, S, 3)); mort = np.zeros((S, S)); r = np.random.default_rng(5)
    hs = []; tot = 0
    while tot < S: h = int(r.choice([44, 52, 60, 68])); hs.append(h); tot += h
    hs[-1] -= tot-S
    y0 = 0
    for h in hs:
        x0 = r.integers(0, S); x = 0
        while x < S:
            L = int(r.integers(60, 150)); L = min(L, S-x) if S-x-L < 40 else L
            tone = np.array([.63, .58, .49])*r.uniform(.8, 1.1) + r.normal(0, .008, 3) + np.array([.02, .01, -.01])*r.uniform(-1, 1)
            xs = (x0+x+np.arange(L)) % S; ys = np.arange(y0, y0+h)
            img[np.ix_(ys, xs)] = tone
            mort[np.ix_(ys, xs)] = 0
            e = 4
            mort[np.ix_(ys[:e], xs)] = 1; mort[np.ix_(ys[-e:], xs)] = 1
            mort[np.ix_(ys, xs[:e])] = 1; mort[np.ix_(ys, xs[-e:])] = 1
            x += L
        y0 += h
    n = fbm(11)[..., None]; n2 = noise(128, 12)[..., None]
    img = img*(.8+.35*n)+.06*(n2-.5)
    img = np.where(mort[..., None] > 0, np.array([.40, .37, .32])*(.8+.3*n), img)
    soot = np.clip(fbm(20)*1.6-.75, 0, 1)[..., None]                       # traces de suie
    return img*(1-.55*soot)
TEX = {}
TEX['Pierre'] = png(stone_tex())
n = fbm(30)[..., None]; stones = (noise(96, 31) > .7)[..., None]; pebbles = (noise(200, 32) > .78)[..., None]
grav = np.array([.42, .39, .34])*(.65+.5*n)
grav = np.where(stones, np.array([.58, .54, .46])*(.8+.3*noise(40, 33)[..., None]), grav)
grav = np.where(pebbles, grav*.6, grav)
TEX['Gravats'] = png(grav)
crack = np.abs(noise(24, 41)-.5) < .025
char = np.array([.06, .05, .045])*(1+.8*fbm(42)[..., None]) + np.array([.10, .05, .02])*(fbm(43)[..., None] > .62)
char = np.where(crack[..., None], np.array([.015, .012, .01]), char)
grain = .5+.5*np.sin(Y/S*2*np.pi*30 + 3*fbm(44))
TEX['Bois_brule'] = png(char*(.85+.3*grain[..., None]))
tile_row = (Y // 64); tx = ((X + (tile_row % 2)*32) % 64)/64; ty = (Y % 64)/64
tl = np.array([.55, .24, .14])*(.75+.35*np.sin(tx*np.pi))[..., None]*(1-.35*(ty > .85))[..., None]
TEX['Tuiles'] = png(tl*(.85+.3*fbm(50)[..., None]))
wd = .5+.5*np.sin(Y/S*2*np.pi*18 + 2*fbm(60))
TEX['Bois'] = png(np.array([.30, .23, .16])*(.75+.35*wd[..., None])*(.8+.3*fbm(61)[..., None]))

# ---------------- géométrie
G = {}
def g(m): return G.setdefault(m, ([], [], [], []))
def quad(mat, V, n, U):
    Pm, Nm, Um, Im = g(mat); b = len(Pm); Pm.extend([tuple(v) for v in V]); Nm.extend([tuple(n)]*4); Um.extend(U)
    A, B_, C = (np.array(V[i]) for i in (0, 1, 2))
    Im.extend([b, b+1, b+2, b, b+2, b+3] if np.dot(np.cross(B_-A, C-A), n) > 0 else [b, b+2, b+1, b, b+3, b+2])
def wbox(mat, x0, y0, z0, x1, y1, z1, uvs=.5):
    """pavé aligné, UV en coordonnées monde (motif continu d'un bloc à l'autre)"""
    for ax in range(3):
        for sd in (0, 1):
            n = [0, 0, 0]; n[ax] = 1 if sd else -1
            lo, hi = [x0, y0, z0], [x1, y1, z1]; c = hi[ax] if sd else lo[ax]
            o = [a for a in range(3) if a != ax]
            V = []
            for (p, q) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                v = [0, 0, 0]; v[ax] = c; v[o[0]] = (lo, hi)[p][o[0]]; v[o[1]] = (lo, hi)[q][o[1]]; V.append(v)
            hu = 2 if ax == 0 else 0                                    # axe horizontal de la face
            U = [((v[hu] if ax != 1 else v[0])*uvs, (v[1] if ax != 1 else v[2])*uvs) for v in V]
            quad(mat, V, n, U)
def rotm(yaw=0, pitch=0, roll=0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]); Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz
def obox(mat, c, size, R, uvs=.9):
    """pavé orienté quelconque (R = matrice 3x3), fil du bois le long de son axe le plus long"""
    h = np.array(size)/2; c = np.array(c, float); L = int(np.argmax(size)); off = rng.random(2)
    for ax in range(3):
        for sd in (-1, 1):
            o = [a for a in range(3) if a != ax]; ua = L if L in o else o[0]; va = o[1] if ua == o[0] else o[0]
            V, U = [], []
            for (p, q) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                lp = np.zeros(3); lp[ax] = sd*h[ax]; lp[o[0]] = p*h[o[0]]; lp[o[1]] = q*h[o[1]]
                V.append(c+R @ lp); U.append((lp[ua]*uvs+off[0], lp[va]*uvs+off[1]))
            n = np.zeros(3); n[ax] = sd; quad(mat, V, R @ n, U)
def beam(mat, a, b, w, h, roll=0.0):
    """poutre de a à b (section w x h)"""
    a, b = np.array(a, float), np.array(b, float); d = b-a; L = np.linalg.norm(d); d /= L
    yaw = math.atan2(d[0], d[2]); pitch = -math.asin(np.clip(d[1], -1, 1))
    obox(mat, (a+b)/2, (w, h, L), rotm(yaw, pitch, roll))

# ---------------- murs en maçonnerie, cassés
CW, CH, TH = .3, .25, .4
def wall(axis, c, u0, u1, outline, openings=(), holes=(), lintels=True):
    """axis 'x' : mur le long de X à z=c ; 'z' : le long de Z à x=c. outline(u) = hauteur restante (cassure comprise)"""
    nrow = int(9.0/CH)+1
    for r in range(nrow):
        v0, v1 = r*CH, (r+1)*CH; vc = (v0+v1)/2; off = (r % 2)*CW/2
        cells = []
        u = u0 - off
        while u < u1:
            a, b = max(u, u0), min(u+CW, u1); uc = (a+b)/2
            keep = vc < outline(uc) + rng.uniform(-.14, .14)
            for (o0, o1, h0, h1) in openings:
                if o0 < uc < o1 and h0 < vc < h1: keep = False
            for (hu, hv, hr) in holes:
                if math.hypot(uc-hu, vc-hv) < hr + rng.uniform(-.18, .18): keep = False
            cells.append((a, b, keep)); u += CW
        run = None
        for a, b, k in cells + [(None, None, False)]:
            if k and run is None: run = [a, b]
            elif k: run[1] = b
            elif run is not None:
                if axis == 'x': wbox('Pierre', run[0], v0, c-TH/2, run[1], v1, c+TH/2)
                else: wbox('Pierre', c-TH/2, v0, run[0], c+TH/2, v1, run[1])
                run = None
    if lintels:
        for (o0, o1, h0, h1) in openings:
            if outline((o0+o1)/2) > h1+.35:
                if axis == 'x': wbox('Pierre', o0-.15, h1, c-TH/2-.01, o1+.15, h1+.22, c+TH/2+.01)
                else: wbox('Pierre', c-TH/2-.01, h1, o0-.15, c+TH/2+.01, h1+.22, o1+.15)
def pl(pts):                                               # ligne de cassure polyligne
    xs, ys = zip(*pts); return lambda u: float(np.interp(u, xs, ys))
EAVE, RIDGE = 5.8, 8.0
gable = lambda u: EAVE + (RIDGE-EAVE)*max(0, 1-abs(u)/3.0)
win_lo = lambda x: (x-.5, x+.5, 1.0, 2.4); win_hi = lambda x: (x-.5, x+.5, 3.8, 5.2)
# façade avant (z=+3) : intacte à gauche, s'effondre vers la droite
front_top = pl([(-4.2, EAVE), (-.3, EAVE), (.6, 5.0), (1.4, 3.6), (2.2, 2.7), (3.0, 2.2), (3.6, 1.5), (4.2, 1.3)])
wall('x', 3.0, -4.2, 4.2, lambda u: min(EAVE, front_top(u)),
     openings=[(-.55, .55, 0, 2.2), win_lo(-2.6), win_lo(2.6), win_hi(-2.6), win_hi(0), win_hi(2.6)], holes=[(-1.4, 4.5, .55)])
# façade arrière (z=-3) : angle arrière gauche écroulé
back_top = pl([(-4.2, 1.0), (-3.4, 1.6), (-2.6, 3.4), (-1.8, EAVE), (1.2, EAVE), (2.4, 4.4), (3.3, 2.9), (4.2, 2.1)])
wall('x', -3.0, -4.2, 4.2, back_top, openings=[win_lo(-1.5), win_lo(2.0), win_hi(-1.5), win_hi(2.0)], holes=[(.4, 2.3, .5)])
# pignon gauche (x=-4) : debout, sauf l'angle arrière ; pignon droit (x=+4) : presque rasé
wall('z', -4.0, -2.8, 2.8, lambda u: min(gable(u), pl([(-2.8, 1.0), (-2.2, 2.0), (-1.4, 4.6), (-.9, 9)])(u)),
     openings=[(1.1, 2.1, 1.0, 2.4), (1.1, 2.1, 3.8, 5.2)], holes=[(1.0, 6.3, .45)])
wall('z', 4.0, -2.8, 2.8, pl([(-2.8, 2.0), (-1.9, 1.3), (-.8, 2.6), (.2, 3.3), (1.2, 2.4), (2.2, 2.9), (2.8, 1.4)]), openings=[(-1.5, -.5, 1.0, 2.4)])
# cheminée sur le pignon gauche, restée debout
cx0, cx1 = -3.8, -3.2
wbox('Pierre', cx0, 0, -.75, cx1, 1.15, -.45); wbox('Pierre', cx0, 0, .45, cx1, 1.15, .75)
wbox('Pierre', cx0, 1.15, -.75, cx1, 1.35, .75); wbox('Pierre', cx0-.02, 1.35, -.6, cx1+.05, 1.42, .6)   # manteau
wbox('Pierre', cx0, 1.42, -.55, cx1-.1, RIDGE+1.2, .55)
wbox('Pierre', cx0-.05, RIDGE+1.2, -.6, cx1-.05, RIDGE+1.32, .6)
wbox('Gravats', cx0+.05, 0, -.45, cx1-.05, .02, .45)                                    # âtre (cendres)
wbox('Gravats', -3.8, 0, -2.8, 3.8, .012, 2.8, .6)                                       # sol du rez-de-chaussée (terre battue, poussière)
# ---------------- plancher de l'étage : solives, planches, partie effondrée en pente
FY = 2.95
for x in np.arange(-3.55, 4, .6):
    if x < -.6: beam('Bois_brule', (x, FY-.12, -2.8), (x, FY-.12, 2.8), .14, .22)
    elif x < 1.0:                                                          # solives cassées, pendantes
        beam('Bois_brule', (x, FY-.12, 2.8), (x+rng.normal(0, .1), FY-.6-rng.uniform(0, .4), .2+rng.uniform(-.3, .3)), .14, .22)
        beam('Bois_brule', (x, FY-.12, -2.8), (x+rng.normal(0, .1), FY-.3-rng.uniform(0, .3), -1.6+rng.uniform(-.3, .3)), .14, .22)
for z in np.arange(-2.75, 2.8, .16):                                      # planches (bord déchiqueté)
    xe = -1.3 + .6*math.sin(z*1.7) + rng.uniform(-.35, .35)
    wbox('Bois', -3.8, FY, z, xe, FY+.03, z+.15, .8)
R = rotm(0, 0, -math.radians(38))                                          # pan de plancher effondré
for i, z in enumerate(np.arange(-1.9, 1.4, .16)):
    L = 2.6 + rng.uniform(-.4, .4); c = np.array([-.45, FY-.1, z+.075]) + R @ np.array([L/2, 0, 0])
    obox('Bois', c, (L, .03, .15), R @ rotm(0, 0, rng.normal(0, .03)))
for z in (-1.6, -.1, 1.1): beam('Bois_brule', (-.5, FY-.2, z), (1.55, FY-1.85, z+rng.normal(0, .2)), .14, .2)
# ---------------- charpente : chevrons calcinés côté gauche, faîtage cassé, bout de toiture
for i, x in enumerate((-3.6, -3.0, -2.4, -1.8)):
    for s in (-1, 1):
        if i == 3 and s < 0: continue
        top = np.array([x, RIDGE-.05, 0.0]); eave = np.array([x, EAVE-.05, s*3.3])
        if s < 0 and x < -1.9:                                              # côté de l'angle écroulé : pendent depuis le faîtage
            beam('Bois_brule', top, (x+rng.normal(0, .15), EAVE-1.0-rng.uniform(0, .8), -2.0-rng.uniform(0, .4)), .1, .14); continue
        if i >= 2: top = eave + (top-eave)*rng.uniform(.55, .8)              # chevrons brisés
        beam('Bois_brule', eave, top, .1, .14)
beam('Bois_brule', (-4.0, RIDGE, 0), (-1.6, RIDGE-.05, 0), .16, .2)
beam('Bois_brule', (-1.6, RIDGE-.05, 0), (-.2, RIDGE-1.9, .4), .16, .2)                   # faîtage pendant
beam('Bois_brule', (-4.2, EAVE+.06, 2.95), (-1.0, EAVE+.06, 2.95), .2, .14)                                    # sablière avant
beam('Bois_brule', (-1.7, EAVE-.1, -2.95), (-4.6, .9, -3.7), .2, .14, .4)                                      # sablière arrière tombée
slope = math.atan2(RIDGE-EAVE, 3.3)
for (x0, x1, f0, f1) in ((-4.15, -2.95, .05, .95), (-2.95, -2.3, .05, .5)):            # restes de toiture (versant avant)
    zc = 3.3*(1-(f0+f1)/2); yc = EAVE + (RIDGE-EAVE)*(f0+f1)/2 + .1; Lr = (f1-f0)*math.hypot(3.3, RIDGE-EAVE)
    obox('Tuiles', ((x0+x1)/2, yc, zc), (x1-x0, .05, Lr), rotm(0, slope, 0), .5)
# ---------------- gravats : tas + blocs + tuiles + poutres au sol
bumps = [(5.0, .2, 1.25, 1.5), (2.2, -.4, 1.35, 1.5), (-4.6, -3.7, .9, 1.1), (3.2, 4.0, .55, 1.1), (-2.9, -2.4, .5, .9), (.8, 3.7, .35, .8)]
def hmound(x, z): return sum(a*np.exp(-((x-bx)**2+(z-bz)**2)/(2*s*s)) for bx, bz, a, s in bumps) - .06
gx = np.linspace(-7.5, 7.5, 61); gz = np.linspace(-6.5, 6.5, 53); GX, GZ = np.meshgrid(gx, gz)
GH = hmound(GX, GZ) + rng.normal(0, .04, GX.shape)*(hmound(GX, GZ) > .1)
Pm, Nm, Um, Im = g('Gravats'); b0 = len(Pm); nx = len(gx)
for j in range(len(gz)):
    for i in range(nx): Pm.append((GX[j, i], max(GH[j, i], -.01), GZ[j, i])); Um.append((GX[j, i]*.6, GZ[j, i]*.6))
tris = []
for j in range(len(gz)-1):
    for i in range(nx-1):
        a, b, c, d = j*nx+i, j*nx+i+1, (j+1)*nx+i, (j+1)*nx+i+1
        if max(GH[j, i], GH[j, i+1], GH[j+1, i], GH[j+1, i+1]) > .005: tris += [a, c, b, b, c, d]
P = np.array(Pm[b0:]); T = np.array(tris).reshape(-1, 3); N = np.zeros_like(P)
for t in T: N[t] += np.cross(P[t[1]]-P[t[0]], P[t[2]]-P[t[0]])
N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9); N[N[:, 1] < 0] *= -1
Nm.extend(N.tolist()); Im.extend((T+b0).ravel().tolist())
hm = lambda x, z: max(0.0, float(hmound(x, z)))
for _ in range(150):                                                       # blocs de pierre
    bx, bz, a, s = bumps[rng.integers(len(bumps))]; x, z = bx+rng.normal(0, s*.8), bz+rng.normal(0, s*.8)
    sz = rng.uniform(.12, .38, 3)*np.array([1.4, .8, 1])
    obox('Pierre', (x, hm(x, z)+sz[1]*.3, z), sz, rotm(rng.uniform(0, 6.3), rng.normal(0, .5), rng.normal(0, .5)), .5)
for _ in range(60):                                                        # morceaux de tuiles
    bx, bz, a, s = bumps[rng.integers(2)]; x, z = bx+rng.normal(0, s), bz+rng.normal(0, s)
    obox('Tuiles', (x, hm(x, z)+.02, z), (rng.uniform(.12, .3), .02, rng.uniform(.15, .35)), rotm(rng.uniform(0, 6.3), rng.normal(0, .4), rng.normal(0, .4)), .5)
for (a, b_) in (((3.4, .3, -2.2), (6.1, 1.4, .8)), ((1.0, .1, 2.0), (3.4, 1.6, -.3)), ((4.5, .2, 2.4), (5.8, .9, 4.0)), ((-5.3, .1, -4.4), (-3.4, .9, -3.2))):
    beam('Bois_brule', a, b_, .14, .2, rng.normal(0, .3))
# ---------------- volet arraché pendant à la fenêtre du rez-de-chaussée gauche
obox('Bois', (-3.25, 1.55, 3.27), (.5, 1.35, .04), rotm(math.radians(-25), 0, math.radians(14)), .9)

# ---------------- meubles réutilisés (table, chaise renversée, lit à l'étage)
def load(fn, R, off, names):
    d = open(fn, 'rb').read(); jl = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20+jl]); B = d[20+jl+8:]
    def A(i):
        a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]; n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}[a['componentType']]
        r = np.frombuffer(B, dt, a['count']*n, v['byteOffset']); return r.reshape(-1, n) if n > 1 else r
    for pr in j['meshes'][0]['primitives']:
        mat = j['materials'][pr['material']]; name = names.get(mat['name'], 'M_'+mat['name'])
        if name not in TEX:
            iv = j['bufferViews'][j['images'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['bufferView']]
            TEX[name] = B[iv['byteOffset']:iv['byteOffset']+iv['byteLength']]
        Pm, Nm, Um, Im = g(name); b = len(Pm)
        Pm.extend((A(pr['attributes']['POSITION']).astype(float) @ R.T + np.array(off)).tolist())
        Nm.extend((A(pr['attributes']['NORMAL']).astype(float) @ R.T).tolist())
        Um.extend(A(pr['attributes']['TEXCOORD_0']).tolist()); Im.extend((A(pr['indices']).astype(int)+b).tolist())
load('tools/modeles/table.glb', rotm(math.radians(8)), (-1.9, 0, -1.2), {})
load('tools/modeles/chaise.glb', rotm(math.radians(30), 0, math.radians(90)), (-2.4, .22, .9), {})     # chaise couchée sur le flanc
load('tools/modeles/lit.glb', rotm(math.radians(3)), (-3.15, FY+.03, -1.45), {})

# ---------------- écriture
_src = "class _M:\n" + open('tools/modeles/make_meubles.py').read().split("class Mesh:\n")[1].split("\nD = '")[0]
_src = _src.replace("I = np.array(Im, np.uint16)", "I = np.array(Im, np.uint32 if len(P) > 65535 else np.uint16)")
_src = _src.replace("'indices': acc(I, 'SCALAR', 5123, 34963)", "'indices': acc(I, 'SCALAR', 5125 if I.dtype == np.uint32 else 5123, 34963)")
_src = _src.replace("'roughnessFactor': .85 if m == 'Bois' else .95", "'roughnessFactor': .95")
exec(_src)
m = _M(); m.G = {k: v for k, v in G.items() if v[3]}
m.write('tools/modeles/maison_detruite.glb', 'MaisonDetruite')
print('matériaux :', ', '.join(m.G))
