"""Chaise et lit low poly (bois assorti à table.glb) -> chaise.glb, lit.glb
Origine au sol au centre, Y en haut, mètres. Chaise : dossier côté +Z. Lit : tête de lit côté -Z."""
import json, struct, io, math, numpy as np
from PIL import Image, ImageFilter
S = 512
def png(a):
    b = io.BytesIO(); Image.fromarray((np.clip(a, 0, 1)*255).astype(np.uint8)).save(b, 'PNG', optimize=True); return b.getvalue()
def noise(cells, seed):
    g = np.tile(np.random.default_rng(seed).random((cells, cells)), (3, 3))
    return np.asarray(Image.fromarray((g*255).astype(np.uint8)).resize((S*3, S*3), Image.BICUBIC), float)[S:2*S, S:2*S]/255
def fbm(seed): return sum(noise(c, seed+i)*a for i, (c, a) in enumerate([(4, .5), (8, .25), (16, .13), (32, .07), (64, .05)]))
y = np.linspace(0, 1, S, endpoint=False)[:, None]; x = np.linspace(0, 1, S, endpoint=False)[None, :]

# --- même bois que table.glb (veines le long de U)
rng = np.random.default_rng(7)
v = np.linspace(0, 1, S)[:, None]; u = np.linspace(0, 1, S)[None, :]
warp = sum(np.sin(2*np.pi*(f*u + rng.random()))*a for f, a in [(1, .05), (3, .02), (7, .008)])
rings = np.sin((v + warp) * 2*np.pi * 18 + np.sin(u*2*np.pi*2)*1.5)
grain = rng.normal(0, 1, (S, S)); grain = np.array(Image.fromarray(((grain*30)+128).clip(0, 255).astype(np.uint8)).resize((S//16, S)).resize((S, S)), float)/255-.5
t = (.55 + .18*rings + .25*grain).clip(0, 1)
WOOD = np.array([.30, .19, .10]) + (np.array([.62, .44, .26])-np.array([.30, .19, .10]))*t[..., None]
# --- drap / matelas : toile de lin écrue, fil fin
weave = (.5+.5*np.sin(x*2*np.pi*128))*(.5+.5*np.sin(y*2*np.pi*128))
LIN = np.array([.80, .77, .70])*(.9+.08*weave[..., None]+.12*(fbm(3)[..., None]-.5))
# --- couverture de laine : rayures, chiné
stripe = ((y*2.2+.05) % 1); band = np.broadcast_to(np.where(stripe < .12, 1, np.where(stripe < .16, 2, 0)), (S, S))
base = np.array([.32, .10, .08]); c1 = np.array([.70, .62, .46]); c2 = np.array([.10, .10, .12])
LAINE = np.where(band[..., None] == 1, c1, np.where(band[..., None] == 2, c2, base))*(.85+.3*(noise(96, 5)[..., None]-.5)+.12*(fbm(9)[..., None]-.5))
# --- matelas : coutil à rayures bleues
TIC = np.where(((x*20) % 1 < .3)[..., None], np.array([.30, .36, .50]), np.array([.78, .76, .70]))*(.92+.1*(fbm(12)[..., None]-.5))
TEX = {'Bois': png(WOOD), 'Lin': png(LIN), 'Laine': png(LAINE), 'Coutil': png(TIC)}

class Mesh:
    def __init__(s): s.G = {}
    def g(s, m): return s.G.setdefault(m, ([], [], [], []))
    def box(s, mat, x0, y0, z0, x1, y1, z1, grain=0, uvs=.9, off=(0, 0)):
        Pm, Nm, Um, Im = s.g(mat)
        F = [((0, 0, -1), [(x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)]), ((0, 0, 1), [(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]),
             ((-1, 0, 0), [(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)]), ((1, 0, 0), [(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)]),
             ((0, 1, 0), [(x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)]), ((0, -1, 0), [(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)])]
        for n, q in F:
            b = len(Pm); ax = [a for a in range(3) if n[a] == 0]
            ua = grain if grain in ax else ax[0]; va = [a for a in ax if a != ua][0]
            for p in q: Pm.append(p); Nm.append(n); Um.append((p[ua]*uvs+off[0]+.37*grain, p[va]*uvs+off[1]))
            Im.extend([b, b+1, b+2, b, b+2, b+3])
    def soft(s, mat, cx, cy, cz, W, H, L, round_=.35, k=12, sag=0.0, uvs=1.0, axis=2):
        """coussin / matelas arrondi : section en super-ellipse extrudée, bouts pincés. axis = axe de la longueur (0 ou 2)"""
        Pm, Nm, Um, Im = s.g(mat); b0 = len(Pm)
        e = 2/(1+round_*3)
        ring = []
        for i in range(k):
            a = 2*math.pi*i/k; ca, sa = math.cos(a), math.sin(a)
            ring.append((math.copysign(abs(ca)**e, ca)*W/2, math.copysign(abs(sa)**e, sa)*H/2))
        ts = [-1, -.92, -.6, 0, .6, .92, 1]
        for t in ts:
            sc = .82 if abs(t) == 1 else 1.0; dip = sag*(1-t*t)
            for i, (a, bq) in enumerate(ring):
                l = t*L/2; px, py = a*sc, bq*sc - (dip if bq > 0 else 0)
                P = (cx+px, cy+py, cz+l) if axis == 2 else (cx+l, cy+py, cz+px)
                Pm.append(P); Um.append(((i/k)*(2*W+2*H)*uvs, (l)*uvs))
        n = len(ts)
        for j in range(n-1):
            for i in range(k):
                a, b = b0+j*k+i, b0+j*k+(i+1) % k
                Im.extend([a, b, a+k, b, b+k, a+k] if axis == 2 else [a, a+k, b, b, a+k, b+k])
        for cap, base in ((0, b0), (1, b0+(n-1)*k)):
            ci = len(Pm); P = (cx, cy, cz+(-1 if cap == 0 else 1)*L/2) if axis == 2 else (cx+(-1 if cap == 0 else 1)*L/2, cy, cz)
            Pm.append(P); Um.append((.5, .5))
            for i in range(k):
                a, b = base+i, base+(i+1) % k
                tri = [ci, b, a] if cap == 0 else [ci, a, b]
                if axis != 2: tri = tri[::-1]
                Im.extend(tri)
        # normales lissées
        P = np.array(Pm[b0:]); I = np.array(Im[-((n-1)*k*6+2*k*3):]).reshape(-1, 3)-b0; N = np.zeros_like(P)
        for tr in I: N[tr] += np.cross(P[tr[1]]-P[tr[0]], P[tr[2]]-P[tr[0]])
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9); Nm.extend(N.tolist())
    def write(s, path, name):
        blob = bytearray(); views, accs = [], []
        def add(data, target=None):
            off = len(blob); blob.extend(data)
            while len(blob) % 4: blob.append(0)
            vv = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
            if target: vv['target'] = target
            views.append(vv); return len(views)-1
        def acc(arr, typ, ct, tg):
            a = {'bufferView': add(arr.tobytes(), tg), 'componentType': ct, 'count': len(arr), 'type': typ}
            if typ == 'VEC3': a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
            accs.append(a); return len(accs)-1
        prims, mats, imgs, tris = [], [], [], 0
        for mi, (m, (Pm, Nm, Um, Im)) in enumerate(s.G.items()):
            P = np.array(Pm, np.float32); N = np.array(Nm, np.float32); U = np.array(Um, np.float32); I = np.array(Im, np.uint16)
            prims.append({'attributes': {'POSITION': acc(P, 'VEC3', 5126, 34962), 'NORMAL': acc(N, 'VEC3', 5126, 34962), 'TEXCOORD_0': acc(U, 'VEC2', 5126, 34962)},
                          'indices': acc(I, 'SCALAR', 5123, 34963), 'material': mi})
            imgs.append({'bufferView': add(TEX[m]), 'mimeType': 'image/png'})
            mats.append({'name': m, 'pbrMetallicRoughness': {'baseColorTexture': {'index': mi}, 'metallicFactor': 0, 'roughnessFactor': .85 if m == 'Bois' else .95}})
            tris += len(I)//3
        j = {'asset': {'version': '2.0', 'generator': 'DEADFRAME make_meubles.py'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
             'nodes': [{'name': name, 'mesh': 0}], 'meshes': [{'name': name, 'primitives': prims}], 'materials': mats,
             'textures': [{'source': i, 'sampler': 0} for i in range(len(imgs))], 'images': imgs,
             'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
             'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(blob)}]}
        js = json.dumps(j, separators=(',', ':')).encode()
        while len(js) % 4: js += b' '
        glb = struct.pack('<III', 0x46546C67, 2, 28+len(js)+len(blob)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(blob), 0x004E4942) + bytes(blob)
        open(path, 'wb').write(glb); print(f'{path.split("/")[-1]} : {len(glb)//1024} Ko, {tris} triangles')

D = 'tools/modeles/'
# ================= CHAISE (assise 44 x 42 cm à 45 cm, dossier à 92 cm, dossier côté +Z)
c = Mesh(); W, Dp, SH, BH, L = .44, .42, .45, .92, .036
hw, hd = W/2, Dp/2
c.box('Bois', -hw, SH-.035, -hd, hw, SH, hd+.01, 0)                                   # assise
for sx in (-1, 1):
    c.box('Bois', sx*hw-L/2-sx*L/2, 0, -hd+.005, sx*hw+L/2-sx*L/2, SH-.035, -hd+.005+L, 1)      # pieds avant
    c.box('Bois', sx*hw-L/2-sx*L/2, 0, hd-L, sx*hw+L/2-sx*L/2, BH, hd, 1)                       # montants arrière (pieds + dossier)
ex = hw-L
for zz in (-hd+.02, hd-.02): c.box('Bois', -ex, SH-.035-.06, zz-.01, ex, SH-.035, zz+.01, 0)   # ceintures
for xx in (-hw+.02, hw-.02): c.box('Bois', xx-.01, SH-.035-.06, -hd+.04, xx+.01, SH-.035, hd-.04, 2)
for xx in (-hw+.018, hw-.018): c.box('Bois', xx-.011, .13, -hd+.04, xx+.011, .155, hd-.04, 2)  # barreaux bas
c.box('Bois', -ex, .2, -.011, ex, .222, .011, 0)
for yy, hh in ((BH-.1, .075), (BH-.30, .05)): c.box('Bois', -ex, yy, hd-L+.006, ex, yy+hh, hd-.008, 0)   # traverses du dossier
for xx in (-.1, 0, .1): c.box('Bois', xx-.017, BH-.30+.05, hd-L+.01, xx+.017, BH-.1, hd-.012, 1)     # barreaux du dossier
c.write(D+'chaise.glb', 'Chaise')

# ================= LIT (une place : couchage 90 x 190, cadre 1,00 x 2,04 m ; tête côté -Z)
b = Mesh(); W, LL, FH = 1.00, 2.04, .40
hw, hl = W/2, LL/2; P = .07
for sz, top in ((-1, 1.0), (1, .62)):                                                  # tête (haute) et pied de lit
    z0 = sz*hl-(P if sz > 0 else 0); z1 = z0+P
    for sx in (-1, 1): b.box('Bois', sx*hw-(P if sx > 0 else 0), 0, z0, sx*hw+(0 if sx > 0 else P), top, z1, 1)
    zc0, zc1 = (z0+.015, z1-.015)
    b.box('Bois', -hw+P, top-.11, zc0, hw-P, top-.03, zc1, 0)                           # traverse haute
    b.box('Bois', -hw+P, FH-.02, zc0, hw-P, FH+.1, zc1, 0)                             # traverse basse
    n = 7 if sz < 0 else 5
    for i in range(n):                                                                  # barreaux
        xx = -hw+P+(i+.5)*(W-2*P)/n
        b.box('Bois', xx-.018, FH+.1, zc0+.012, xx+.018, top-.11, zc1-.012, 1)
    for sx in (-1, 1): b.box('Bois', sx*hw-(P if sx > 0 else 0)-.006, top, z0-.006, sx*hw+(0 if sx > 0 else P)+.006, top+.025, z1+.006, 0)  # chapeaux
for sx in (-1, 1): b.box('Bois', sx*(hw-.012)-.022, FH-.17, -hl+P, sx*(hw-.012)+.022, FH, hl-P, 2)    # longerons
for i in range(9): zz = -hl+P+.1+i*(LL-2*P-.2)/8; b.box('Bois', -hw+.035, FH-.035, zz-.04, hw-.035, FH-.015, zz+.04, 0)  # lattes
MT = .16; my = FH-.015+MT/2
b.soft('Coutil', 0, my, 0, W-.1, MT, LL-2*P-.04, round_=.18, k=16)                      # matelas
b.soft('Lin', 0, my+MT/2+.055, -hl+P+.3, .62, .13, .40, round_=.55, k=14, sag=.025, axis=0)   # oreiller (en travers)
# drap rabattu + couverture : nappes posées sur le matelas, retombant sur les côtés
top = my+MT/2
def sheet(mat, z0, z1, y, over, drop, uvs=1.0):
    hx = (W-.1)/2+over
    b.box(mat, -hx, y, z0, hx, y+.012, z1, 0, uvs)
    for sx in (-1, 1): b.box(mat, sx*hx-(.012 if sx > 0 else 0), y-drop, z0, sx*hx+(0 if sx > 0 else .012), y+.012, z1, 1, uvs)
sheet('Laine', -hl+P+.62, hl-P-.02, top+.004, .025, .27, 1.0)
b.box('Laine', -(W-.1)/2-.037, top+.004-.27, hl-P-.032, (W-.1)/2+.037, top+.016, hl-P-.02, 0, 1.0)  # retombée au pied
sheet('Lin', -hl+P+.48, -hl+P+.66, top+.016, .03, .26)                                  # revers du drap sur la couverture
b.write(D+'lit.glb', 'Lit')
