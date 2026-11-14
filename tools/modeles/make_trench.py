"""Tranchée 14-18 : ligne droite + virages à gauche et à droite, raccordables -> tranchee*.glb
Convention commune : on entre par z=+4 (centre x=0) en marchant vers -Z ; parapet (sacs de sable) à gauche du sens de marche.
Fond à y=0, sol extérieur à y=DEPTH. Les virages pivotent en (0,0) et sortent par x=-4 (gauche) ou x=+4 (droite)."""
import json, struct, io, math, numpy as np
from PIL import Image, ImageFilter
LEN, DEPTH, HALF_W, OUT = 8.0, 2.0, 0.62, 3.0   # longueur, profondeur, demi-largeur du fond, demi-largeur totale
rng = np.random.default_rng(14)

# ---------------- textures procédurales (raccordables)
def noise(S, cells, seed):
    r = np.random.default_rng(seed); g = r.random((cells, cells)); g = np.tile(g, (3, 3))
    im = Image.fromarray((g*255).astype(np.uint8)).resize((S*3, S*3), Image.BICUBIC)
    return np.asarray(im, float)[S:2*S, S:2*S]/255
def fbm(S, seed): return sum(noise(S, c, seed+i)*a for i, (c, a) in enumerate([(4, .5), (8, .25), (16, .13), (32, .07), (64, .05)]))
def png(a):
    b = io.BytesIO(); Image.fromarray((a.clip(0, 1)*255).astype(np.uint8)).save(b, 'PNG', optimize=True); return b.getvalue()
S = 512
n = fbm(S, 1); n2 = fbm(S, 9)
earth = np.array([.27, .20, .13])*(.6+.7*n[..., None]) + np.array([.05, .04, .02])*(n2[..., None]-.5)
stones = (noise(S, 128, 3)*.7+noise(S, 64, 5)*.3 > .8)[..., None]; earth = np.where(stones, earth*1.18+.015, earth)
clods = fbm(S, 77)[..., None]; earth = earth*(.85+.3*clods)
y = np.arange(S)[:, None]/S; x = np.arange(S)[None, :]/S
wp = fbm(S, 55); w = .5+.5*np.sin((y + .06*(wp-.5) + .01*np.sin(x*2*np.pi*2))*2*np.pi*22); g = fbm(S, 21)
streak = noise(S, 8, 61)[:, :1].repeat(S, 1)*0 + np.asarray(Image.fromarray((np.random.default_rng(3).random((S, 16))*255).astype(np.uint8)).resize((S, S), Image.BICUBIC), float)/255
wood = (np.array([.22, .17, .12]) + np.array([.17, .13, .09])*(w*.35+g*.45+streak*.35)[..., None])*np.array([1, .98, .92])
weave = (np.sin(x*2*np.pi*96)*np.sin(y*2*np.pi*96))[..., None]
sack = np.array([.52, .44, .30])*(.8+.08*weave+.35*(fbm(S, 33)[..., None]-.5)) - .12*(fbm(S, 40)[..., None] > .62)
TEX = {'Terre': png(earth), 'Bois': png(wood), 'Sacs': png(sack)}
for k, v in TEX.items(): open(f'tools/modeles/tex_{k}.png', 'wb').write(v)

G = {k: ([], [], [], []) for k in TEX}         # P, N, UV, I par matériau
def tri_mesh(mat, P, UV, I):
    Pm, Nm, Um, Im = G[mat]; b = len(Pm)
    P = np.asarray(P, float); I = np.asarray(I, int).reshape(-1, 3)
    N = np.zeros_like(P)
    for t in I:
        fn = np.cross(P[t[1]]-P[t[0]], P[t[2]]-P[t[0]]); N[t] += fn
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    Pm.extend(P.tolist()); Nm.extend(N.tolist()); Um.extend(np.asarray(UV, float).tolist()); Im.extend((I+b).ravel().tolist())
def box(mat, c, size, uvs=1.0, rot=0.0):
    """pavé centré en c, taille size, rotation rot autour de Y ; faces à normales franches"""
    hx, hy, hz = np.array(size)/2; Pm, Nm, Um, Im = G[mat]
    cr, sr = math.cos(rot), math.sin(rot); R = lambda v: np.array([v[0]*cr+v[2]*sr, v[1], -v[0]*sr+v[2]*cr])
    F = [((0, 0, -1), [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]), ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
         ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]), ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
         ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]), ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)])]
    off = rng.random(2)
    for nrm, q in F:
        b = len(Pm); ax = [a for a in range(3) if nrm[a] == 0]
        ua = 2 if 2 in ax and size[2] >= max(size[0], size[1]) else (0 if 0 in ax and size[0] >= size[1] else ax[0])
        va = [a for a in ax if a != ua][0]
        for s in q:
            lp = np.array(s)*[hx, hy, hz]; Pm.append((R(lp)+c).tolist()); Nm.append(R(np.array(nrm, float)).tolist())
            Um.append([lp[ua]*uvs+off[0], lp[va]*uvs+off[1]])
        Im.extend([b, b+1, b+2, b, b+2, b+3])

# --- sacs de sable sur le parapet (prismes à 8 côtés aplatis)
def sandbag(c, L=.55, W=.32, H=.17, rot=0.0):
    Pm = []; UVm = []; I = []; k = 10
    ring = [(math.cos(2*math.pi*i/k)*W/2*(1-.12*abs(math.sin(2*math.pi*i/k))), math.sin(2*math.pi*i/k)*H/2) for i in range(k)]
    cr, sr = math.cos(rot), math.sin(rot)
    for j, t in enumerate((-1, -.8, .8, 1)):
        sc = .55 if abs(t) == 1 else 1.0
        for i, (a, b) in enumerate(ring):
            lx, ly, lz = a*sc, b*sc, t*L/2
            Pm.append((c[0]+lx*cr+lz*sr, c[1]+ly, c[2]-lx*sr+lz*cr)); UVm.append((i/k*1.4, (t+1)*.6))
    for j in range(3):
        for i in range(k):
            a, b = j*k+i, j*k+(i+1) % k; I += [a, b, a+k, b, b+k, a+k]
    for cap, base in ((0, 0), (1, 3*k)):
        ci = len(Pm); cz = (-1 if cap == 0 else 1)*L/2; Pm.append((c[0]+cz*sr, c[1], c[2]+cz*cr)); UVm.append((.5, .5))
        for i in range(k):
            a, b = base+i, base+(i+1) % k; I += ([ci, b, a] if cap == 0 else [ci, a, b])
    tri_mesh('Sacs', Pm, UVm, I)

def write_glb(path):
    blob = bytearray(); views, accs = [], []
    def add(data, target=None):
        off = len(blob); blob.extend(data)
        while len(blob) % 4: blob.append(0)
        v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
        if target: v['target'] = target
        views.append(v); return len(views)-1
    def acc(arr, typ, ct, tg):
        a = {'bufferView': add(arr.tobytes(), tg), 'componentType': ct, 'count': len(arr), 'type': typ}
        if typ == 'VEC3': a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
        accs.append(a); return len(accs)-1
    prims, mats, imgs, tris = [], [], [], 0
    for mi, (name, (Pm, Nm, Um, Im)) in enumerate(G.items()):
        P = np.array(Pm, np.float32); N = np.array(Nm, np.float32); U = np.array(Um, np.float32); I = np.array(Im, np.uint32 if len(P) > 65535 else np.uint16)
        prims.append({'attributes': {'POSITION': acc(P, 'VEC3', 5126, 34962), 'NORMAL': acc(N, 'VEC3', 5126, 34962), 'TEXCOORD_0': acc(U, 'VEC2', 5126, 34962)},
                      'indices': acc(I, 'SCALAR', 5125 if I.dtype == np.uint32 else 5123, 34963), 'material': mi})
        imgs.append({'bufferView': add(TEX[name]), 'mimeType': 'image/png'})
        mats.append({'name': name, 'pbrMetallicRoughness': {'baseColorTexture': {'index': mi}, 'metallicFactor': 0, 'roughnessFactor': .95}})
        tris += len(I)//3
    j = {'asset': {'version': '2.0', 'generator': 'DEADFRAME make_trench.py'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
         'nodes': [{'name': 'Tranchee', 'mesh': 0}], 'meshes': [{'name': 'Tranchee', 'primitives': prims}], 'materials': mats,
         'textures': [{'source': i, 'sampler': 0} for i in range(len(imgs))], 'images': imgs,
         'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
         'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(blob)}]}
    js = json.dumps(j, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    glb = struct.pack('<III', 0x46546C67, 2, 28+len(js)+len(blob)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(blob), 0x004E4942) + bytes(blob)
    open(path, 'wb').write(glb)
    print(f'{path.split("/")[-1]} : {len(glb)//1024} Ko, {tris} triangles')

# ---------------- géométrie
PROF = [(-OUT, DEPTH+.05), (-2.2, DEPTH+.12), (-1.5, DEPTH+.02), (-1.0, DEPTH), (-.78, DEPTH-.12), (-HALF_W-.06, 1.85), (-HALF_W-.06, .05), (-HALF_W+.05, 0),
        (HALF_W-.05, 0), (HALF_W+.06, .05), (HALF_W+.06, 1.85), (.85, DEPTH-.05), (1.3, DEPTH+.25), (1.9, DEPTH+.35), (2.5, DEPTH+.15), (OUT, DEPTH+.05)]

def build(path, out):
    global G, rng
    rng = np.random.default_rng(14); G = {k: ([], [], [], []) for k in TEX}
    C = [np.array(p, float) for p in path]                      # tracé (x, z)
    segs = [(C[i], C[i+1]) for i in range(len(C)-1)]
    dirs = [(b-a)/np.linalg.norm(b-a) for a, b in segs]
    right = lambda d: np.array([-d[1], d[0]])                     # marche vers -Z -> droite = +X
    def offset(px):
        pts = [C[0]+right(dirs[0])*px]
        for i in range(1, len(C)-1):
            r1, r2 = right(dirs[i-1]), right(dirs[i]); pts.append(C[i]+(r1+r2)/(1+r1@r2)*px)
        return pts+[C[-1]+right(dirs[-1])*px]
    seglen = [np.linalg.norm(b-a) for a, b in segs]; TOT = sum(seglen)
    ns = [max(1, round(l/.25)) for l in seglen]

    # --- terre : profil balayé le long du tracé (onglet à 45° dans les coins)
    arc = np.concatenate([[0], np.cumsum([math.dist(PROF[i], PROF[i+1]) for i in range(len(PROF)-1)])])
    rows = []                                                     # rangées transversales
    for si in range(len(segs)):
        for j in range(ns[si] + (1 if si == len(segs)-1 else 0)):
            rows.append((si, j/ns[si], sum(seglen[:si]) + seglen[si]*j/ns[si]))
    OFF = [offset(px) for px, _ in PROF]
    P, UV = [], []
    for si, t, dist in rows:
        env = math.sin(math.pi*dist/TOT)
        for k, (px, py) in enumerate(PROF):
            a, b = OFF[k][si], OFF[k][si+1]; q = a+(b-a)*t
            jy = (rng.normal(0, .07) if abs(px) > 1.0 else rng.normal(0, .02) if py < .06 else 0)*env
            P.append((q[0], py+jy, q[1])); UV.append((arc[k]*.5, -dist*.5))
    I = []; M = len(PROF)
    for i in range(len(rows)-1):
        for k in range(M-1):
            a, b = i*M+k, i*M+k+1; c, d = a+M, b+M; I += [a, b, c, b, d, c]
    tri_mesh('Terre', P, UV, I)

    rotof = lambda d: math.atan2(d[0], d[1])                      # axe local Z du pavé -> direction d
    # --- coffrage : planches par panneaux de 2 m max, poteaux aux jonctions et dans les coins
    for s in (-1, 1):
        wl = offset(s*(HALF_W+.035)); pl = offset(s*(HALF_W-.02))
        for i in range(len(wl)-1):
            a, b = wl[i], wl[i+1]; L = np.linalg.norm(b-a); d = (b-a)/L; npn = max(1, math.ceil(L/2.0-1e-6))
            ext0 = .02 if i > 0 else 0; ext1 = .02 if i < len(wl)-2 else 0
            for p in range(npn):
                t0, t1 = p/npn*L - (ext0 if p == 0 else 0), (p+1)/npn*L + (ext1 if p == npn-1 else 0)
                c = a+d*(t0+t1)/2
                for row in range(8):
                    yc = .14+row*.225+rng.normal(0, .008)
                    box('Bois', (c[0], yc, c[1]), (.035, .2, t1-t0-.01), .9, rotof(d)+rng.normal(0, .004))
            pa, pb = pl[i], pl[i+1]; PL = np.linalg.norm(pb-pa); pd = (pb-pa)/PL
            for p in range(npn+1):
                if p == 0 and i > 0: continue
                tt = np.clip(p/npn*PL, .06, PL-.06); q = pa+pd*tt
                box('Bois', (q[0], .95, q[1]), (.12, 1.9+rng.uniform(0, .12), .12), .8, rotof(pd)+rng.normal(0, .03))
    # --- caillebotis : modules d'environ 1 m, carré à part dans chaque coin
    for si, (a, b) in enumerate(segs):
        d = dirs[si]; L = seglen[si]; t0 = .5 if si > 0 else 0; t1 = L-(.5 if si < len(segs)-1 else 0)
        n = max(1, round(t1-t0)); ml = (t1-t0)/n
        for m in range(n):
            c = a+d*(t0+(m+.5)*ml)
            for s in (-1, 1):
                q = c+right(d)*s*.3; box('Bois', (q[0], .05, q[1]), (.07, .09, ml-.02), 1.2, rotof(d))
            for k in range(round(ml/.168)):
                q = c+d*(-ml/2+.084+k*ml/round(ml/.168)); box('Bois', (q[0]+rng.normal(0, .01), .115, q[1]), (.92, .04, .1), 1.2, rotof(d)+rng.normal(0, .025))
    for i in range(1, len(C)-1):
        c = C[i]; d = dirs[i-1]
        for s in (-1, 1):
            q = c+right(d)*s*.3; box('Bois', (q[0], .05, q[1]), (.07, .09, .98), 1.2, rotof(d))
        for k in range(6):
            q = c+d*(-.42+k*.168); box('Bois', (q[0], .115, q[1]), (.92, .04, .1), 1.2, rotof(d)+rng.normal(0, .025))
    # --- sacs de sable (côté parapet = gauche = px négatif)
    def along(px, step, start, cb):
        pts = offset(px); lens = [np.linalg.norm(pts[i+1]-pts[i]) for i in range(len(pts)-1)]; total = sum(lens); t = start
        while t < total-.27:
            acc = 0
            for i, l in enumerate(lens):
                if t <= acc+l or i == len(lens)-1:
                    d = (pts[i+1]-pts[i])/l; cb(pts[i]+d*(t-acc), d); break
                acc += l
            t += step
    for layer in range(3):
        along(-1.02+layer*.04, .58, .29+(.29 if layer % 2 else 0),
              lambda q, d, y=DEPTH+.07+layer*.155: sandbag((q[0]+rng.normal(0, .02), y, q[1]), rot=rotof(d)+math.pi/2+rng.normal(0, .06)))
    along(-1.42, .62, .35, lambda q, d: sandbag((q[0], DEPTH+.12, q[1]+rng.normal(0, .02)), rot=rotof(d)+rng.normal(0, .08)))
    write_glb(out)


D = 'tools/modeles/'
build([(0, LEN/2), (0, -LEN/2)], D+'tranchee.glb')
build([(0, LEN/2), (0, 0), (-LEN/2, 0)], D+'tranchee_virage_gauche.glb')
build([(0, LEN/2), (0, 0), (LEN/2, 0)], D+'tranchee_virage_droite.glb')
