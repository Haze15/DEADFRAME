"""Terrain boueux (no man's land) -> terrain_boue.glb
Tuile de SIZE x SIZE m centrée en (0,0), bords à y=0 et à plat (tuiles juxtaposables). Y en haut, mètres."""
import json, struct, io, math, numpy as np
from PIL import Image
SIZE, STEP, SEED = 32.0, .4, 1917                       # taille, résolution du maillage, graine (autre graine = autre terrain)
rng = np.random.default_rng(SEED); S = 512
def png(a):
    b = io.BytesIO(); im = Image.fromarray((np.clip(a, 0, 1)*255).astype(np.uint8))
    if a.shape[0] > 1024: im.save(b, 'JPEG', quality=88); return b.getvalue()
    im.save(b, 'PNG', optimize=True); return b.getvalue()
def noise(cells, seed, size=S):
    g = np.tile(np.random.default_rng(seed).random((cells, cells)), (3, 3))
    return np.asarray(Image.fromarray((g*255).astype(np.uint8)).resize((size*3, size*3), Image.BICUBIC), float)[size:2*size, size:2*size]/255
def fbm(seed, size=S): return sum(noise(c, seed+i, size)*a for i, (c, a) in enumerate([(4, .5), (8, .25), (16, .13), (32, .07), (64, .05)]))
yy, xx = np.mgrid[0:S, 0:S]/S

# ---------------- textures de détail (raccordables, 4 m)
n1, n2 = fbm(1), fbm(2)
crk = (np.abs(noise(28, 3)-.5) < .008) & (fbm(12) > .55)                 # fines craquelures, par plaques
peb = noise(300, 4) > .9
terre = np.array([.24, .18, .125])*(.8+.35*n1[..., None]) + .05*(noise(160, 13)[..., None]-.5) + np.array([.02, .015, .01])*(n2[..., None]-.5)
terre = np.where(peb[..., None], terre*1.12, terre)
terre = np.where(crk[..., None], terre*.7, terre)
hl = np.clip((noise(40, 6)-.6)*3, 0, 1)
boue = np.array([.13, .095, .065])*(.8+.4*fbm(5)[..., None]) + .06*(noise(140, 14)[..., None]-.5) + .07*hl[..., None]
eau = np.array([.085, .07, .05])*(.85+.25*fbm(8)[..., None]) + .07*np.clip((noise(10, 9)-.55)*3, 0, 1)[..., None]
wd = .5+.5*np.sin(yy*2*np.pi*14 + 2*fbm(10))
bois = np.array([.20, .15, .10])*(.7+.4*wd[..., None])*(.8+.3*fbm(11)[..., None])
TEX = {'Terre': png(terre), 'Eau': png(eau), 'Bois': png(bois)}

# ---------------- relief
H = SIZE/2
def smooth_field(cells, seed, amp):
    g = np.random.default_rng(seed).random((cells, cells)).astype(np.float32)
    im = Image.fromarray(g, 'F').resize((257, 257), Image.BICUBIC); a = np.asarray(im, float)
    return lambda x, z: amp*(a[np.clip(((z+H)/SIZE*256).astype(int), 0, 256), np.clip(((x+H)/SIZE*256).astype(int), 0, 256)]-.5)
base1, base2 = smooth_field(5, SEED+1, .9), smooth_field(13, SEED+2, .35)
craters = []
for _ in range(400):                                           # placement sans trop de recouvrement
    R = rng.choice([1.3, 1.8, 2.4, 3.2, 4.2], p=[.3, .28, .2, .14, .08]); x, z = rng.uniform(-H+R+3, H-R-3, 2)
    if all(math.hypot(x-cx, z-cz) > (R+cr)*.75 for cx, cz, cr, _ in craters): craters.append((x, z, R, R*rng.uniform(.32, .42)))
    if len(craters) >= 14: break
def crater_field(x, z):
    c = np.zeros_like(x)
    for cx, cz, R, d in craters:
        r = np.hypot(x-cx, z-cz)/R
        bowl = -d*np.clip(1-r*r, 0, None)**1.3
        rim = .3*d*np.exp(-((r-1.05)/.32)**2)
        c += bowl + rim
    return c
def env(x, z):                                                 # bords à 0 et à plat
    e = lambda v: np.clip((H-np.abs(v))/3.0, 0, 1)**2*(3-2*np.clip((H-np.abs(v))/3.0, 0, 1))
    return e(x)*e(z)
def height(x, z): return env(x, z)*(base1(x, z)+base2(x, z)+crater_field(x, z))

N = int(round(SIZE/STEP))+1; g1 = np.linspace(-H, H, N); GX, GZ = np.meshgrid(g1, g1)
GH = height(GX, GZ)
dzx = np.gradient(GH, STEP, axis=1); dzz = np.gradient(GH, STEP, axis=0)
NRM = np.stack([-dzx, np.ones_like(GH), -dzz], -1); NRM /= np.linalg.norm(NRM, axis=-1, keepdims=True)

G = {}
def g(m): return G.setdefault(m, ([], [], [], []))
# texture unique de la tuile : terre / boue mélangées selon les cratères, terre fraîche sur les bourrelets
TS = 2048; px = (np.arange(TS)+.5)/TS*SIZE-H; PX, PZ = np.meshgrid(px, px)
rep = TS//int(SIZE/4)                                                       # pixels par motif de 4 m
def tiled(arr):
    t = np.asarray(Image.fromarray((np.clip(arr, 0, 1)*255).astype(np.uint8)).resize((rep, rep), Image.LANCZOS), float)/255
    return np.tile(t, (TS//rep, TS//rep, 1))
T_terre, T_boue = tiled(terre), tiled(boue)
cf = crater_field(PX, PZ); ev = env(PX, PZ)
blot = np.asarray(Image.fromarray((np.random.default_rng(SEED+3).random((20, 20))*255).astype(np.uint8)).resize((TS, TS), Image.BICUBIC), float)/255
fine = np.asarray(Image.fromarray((np.random.default_rng(SEED+4).random((90, 90))*255).astype(np.uint8)).resize((TS, TS), Image.BICUBIC), float)/255
wet = np.clip((-cf-.12)/.35 + (blot-.68)*3.0 + (fine-.5)*.8, 0, 1)*ev       # fond des cratères + flaques de boue
rimm = np.clip(cf/.25, 0, 1)*ev                                             # bourrelets : terre retournée, plus claire
ao = np.clip(1+cf*.35, .55, 1)                                              # creux plus sombres
col = T_terre*(1-wet[..., None]) + T_boue*wet[..., None]
col = col*(1+.14*rimm[..., None])*ao[..., None]
TEX['Sol'] = png(col)
Pm, Nm, Um, Im = g('Sol')
for j in range(N):
    for i in range(N): Pm.append((GX[j, i], GH[j, i], GZ[j, i])); Nm.append(tuple(NRM[j, i])); Um.append(((GX[j, i]+H)/SIZE, (GZ[j, i]+H)/SIZE))
for j in range(N-1):
    for i in range(N-1):
        a, b, c, d = j*N+i, j*N+i+1, (j+1)*N+i, (j+1)*N+i+1; Im.extend([a, c, b, b, c, d])

# ---------------- flaques au fond des gros cratères
for cx, cz, R, d in craters:
    if R < 2.3: continue
    level = float(height(np.array(cx), np.array(cz))) + .3*d
    rw = R*.62; k = 28
    Pm, Nm, Um, Im = g('Eau'); b = len(Pm); Pm.append((cx, level, cz)); Nm.append((0, 1, 0)); Um.append((cx*.2, cz*.2))
    for t in range(k):
        a = 2*math.pi*t/k; rr = rw*(1+.08*math.sin(3*a+cx)+.05*math.sin(5*a+cz))
        Pm.append((cx+rr*math.cos(a), level, cz+rr*math.sin(a))); Nm.append((0, 1, 0)); Um.append(((cx+rr*math.cos(a))*.2, (cz+rr*math.sin(a))*.2))
    for t in range(k): Im.extend([b, b+1+(t+1) % k, b+1+t])

# ---------------- mottes, cailloux, piquets cassés
def quad(mat, V, n, U):
    Pm, Nm, Um, Im = g(mat); b = len(Pm); Pm.extend([tuple(v) for v in V]); Nm.extend([tuple(n)]*4); Um.extend(U)
    A, B_, C = (np.array(V[i]) for i in (0, 1, 2))
    Im.extend([b, b+1, b+2, b, b+2, b+3] if np.dot(np.cross(B_-A, C-A), n) > 0 else [b, b+2, b+1, b, b+3, b+2])
def rotm(yaw=0, pitch=0, roll=0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    return np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
def obox(mat, c, size, R, uvs=1.0):
    h = np.array(size)/2; c = np.array(c, float); L = int(np.argmax(size)); off = rng.random(2)
    for ax in range(3):
        for sd in (-1, 1):
            o = [a for a in range(3) if a != ax]; ua = L if L in o else o[0]; va = o[1] if ua == o[0] else o[0]
            V, U = [], []
            for (p, q) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                lp = np.zeros(3); lp[ax] = sd*h[ax]; lp[o[0]] = p*h[o[0]]; lp[o[1]] = q*h[o[1]]
                V.append(c+R @ lp); U.append((lp[ua]*uvs+off[0], lp[va]*uvs+off[1]))
            n = np.zeros(3); n[ax] = sd; quad(mat, V, R @ n, U)
hgt = lambda x, z: float(height(np.array(x), np.array(z)))
def clod(c, size, R, nl=4, nu=7):
    """motte de terre : sphère grossière déformée et aplatie"""
    Pm, Nm, Um, Im = g('Terre'); b = len(Pm); c = np.array(c, float); h = np.array(size)/2
    pts = [(0, 1, 0)]
    for i in range(1, nl):
        th = math.pi*i/nl
        for k in range(nu):
            ph = 2*math.pi*k/nu + i*.4; pts.append((math.sin(th)*math.cos(ph), math.cos(th), math.sin(th)*math.sin(ph)))
    pts.append((0, -1, 0)); pts = np.array(pts)*rng.uniform(.75, 1.15, (len(pts), 1))
    V = c + (pts*h) @ R.T; off = rng.random(2)
    for v in V: Pm.append(tuple(v)); Um.append((v[0]*1.5+off[0], v[2]*1.5+v[1]+off[1]))
    T = []
    for k in range(nu): T.append((0, 1+(k+1) % nu, 1+k))
    for i in range(nl-2):
        for k in range(nu):
            a, b2 = 1+i*nu+k, 1+i*nu+(k+1) % nu; T += [(a, b2, a+nu), (b2, b2+nu, a+nu)]
    last = len(pts)-1; base = 1+(nl-2)*nu
    for k in range(nu): T.append((last, base+k, base+(k+1) % nu))
    T = np.array(T); Nv = np.zeros_like(V)
    for t in T:
        fn = np.cross(V[t[1]]-V[t[0]], V[t[2]]-V[t[0]])
        if np.dot(fn, V[t].mean(0)-c) < 0: t[1], t[2] = t[2], t[1]; fn = -fn
        Nv[t] += fn
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-9); Nm.extend(Nv.tolist()); Im.extend((T+b).ravel().tolist())
for cx, cz, R, d in craters:                                   # mottes projetées autour des cratères
    for _ in range(int(R*5)):
        a = rng.uniform(0, 2*math.pi); r = R*rng.uniform(.95, 1.9); x, z = cx+r*math.cos(a), cz+r*math.sin(a)
        if max(abs(x), abs(z)) > H-1.5: continue
        s = rng.uniform(.12, .32)
        clod((x, hgt(x, z)+s*.12, z), (s*rng.uniform(1, 1.6), s*.6, s), rotm(rng.uniform(0, 6.3), rng.normal(0, .3), rng.normal(0, .3)))
for _ in range(10):                                            # piquets cassés plantés de travers
    x, z = rng.uniform(-H+3, H-3, 2); h = rng.uniform(.5, 1.3)
    R = rotm(rng.uniform(0, 6.3), rng.normal(0, .25), rng.normal(0, .25))
    obox('Bois', np.array([x, hgt(x, z), z]) + R @ np.array([0, h/2-.15, 0]), (.08, h, .08), R)

# ---------------- écriture (eau et boue plus brillantes)
_src = "class _M:\n" + open('tools/modeles/make_meubles.py').read().split("class Mesh:\n")[1].split("\nD = '")[0]
_src = _src.replace("I = np.array(Im, np.uint16)", "I = np.array(Im, np.uint32 if len(P) > 65535 else np.uint16)")
_src = _src.replace("'indices': acc(I, 'SCALAR', 5123, 34963)", "'indices': acc(I, 'SCALAR', 5125 if I.dtype == np.uint32 else 5123, 34963)")
_src = _src.replace("'mimeType': 'image/png'", "'mimeType': 'image/jpeg' if TEX[m][:2] == bytes([255, 216]) else 'image/png'")
_src = _src.replace("'roughnessFactor': .85 if m == 'Bois' else .95", "'roughnessFactor': {'Eau': .08}.get(m, .9)")
exec(_src)
m = _M(); m.G = {k: v for k, v in G.items() if v[3]}
m.write('tools/modeles/terrain_boue.glb', 'TerrainBoue')
print(f'{len(craters)} cratères, relief de {GH.min():.2f} à {GH.max():.2f} m')
