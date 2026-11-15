"""Hôpital abandonné (GLB fourni) -> modèle du décor + boîtes de collision + points d'apparition + lumières.

Usage : python3 tools/hopital.py <hopital.glb> <dossier assets> <sortie json>
Les collisions sont obtenues en voxélisant la géométrie (cases de 0,2 m) puis en fusionnant les cases pleines
en boîtes (fusion gloutonne x -> z -> y). Le sol extérieur (y < 0,1 m), l'herbe, les papiers et les gravats ne
bloquent pas."""
import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from convert import GLB, gather_static, convert_static

src, outdir, outjson = sys.argv[1:4]
R = .2
RY = .1  # pas vertical plus fin : hauteurs de marches exactes à 10 cm près
RV = np.array([R, RY, R])
NOCOL = {'Terrain', 'Herbe', 'Papier', 'Gravats', 'Arbre_Bois_eclate', 'Voit_Feu'}

convert_static(src, 'hop_map', outdir, 10 ** 9, tex=512)

g = GLB(src)
P, N, UV, MAT, IDX, mats = gather_static(g)
names = [g.j['materials'][m]['name'] for m in mats]
keep = np.array([names[MAT[t[0]]] not in NOCOL for t in IDX])
T = P[IDX[keep]]  # (n,3,3)
lo = np.array([-45.2, -0.4, -48.2]); hi = np.array([45.2, 11.6, 43.4])
dims = np.ceil((hi - lo) / RV).astype(int)
G = np.zeros(dims, bool)
# échantillonnage des surfaces : chaque triangle subdivisé pour un pas d'au plus R/2.5
e = np.maximum(np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.maximum(np.linalg.norm(T[:, 2] - T[:, 1], axis=1), np.linalg.norm(T[:, 0] - T[:, 2], axis=1)))
nsub = np.clip(np.ceil(e / (RY / 2)).astype(int), 1, 800)
for n in np.unique(nsub):
    tri = T[nsub == n]
    a, b = np.meshgrid(np.arange(n + 1), np.arange(n + 1))
    m = (a + b) <= n
    u, v = (a[m] / n), (b[m] / n)
    pts = tri[:, None, 0] * (1 - u - v)[None, :, None] + tri[:, None, 1] * u[None, :, None] + tri[:, None, 2] * v[None, :, None]
    ix = np.floor((pts.reshape(-1, 3) - lo) / RV).astype(int)
    ok = np.all((ix >= 0) & (ix < dims), 1)
    ix = ix[ok]
    G[ix[:, 0], ix[:, 1], ix[:, 2]] = True
G[:, :int(np.ceil((0.06 - lo[1]) / RY)), :] = False   # le sol (plan y = 0 du jeu)
print('cases pleines', int(G.sum()))

# fusion gloutonne
boxes = []
nx, ny, nz = dims
prev = {}  # rectangles du niveau y précédent : (x0,x1,z0,z1) -> index de boîte
for y in range(ny):
    L = G[:, y, :]
    rects = []
    spans_prev = {}
    open_ = {}
    for z in range(nz):
        col = L[:, z]
        if not col.any():
            cur = {}
        else:
            d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
            st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
            cur = {}
            for x0, x1 in zip(st, en):
                k = (x0, x1)
                cur[k] = open_.get(k, z)
        for k, z0 in open_.items():
            if k not in cur:
                rects.append((k[0], k[1], z0, z))
        open_ = cur
    for k, z0 in open_.items():
        rects.append((k[0], k[1], z0, nz))
    cur = {}
    for r in rects:
        if r in prev:
            bi = prev[r]; boxes[bi][4] = y + 1; cur[r] = bi
        else:
            boxes.append([r[0], y, r[2], r[1], y + 1, r[3]]); cur[r] = len(boxes) - 1
    prev = cur
B = np.array(boxes, float)
B[:, [0, 3]] = B[:, [0, 3]] * R + lo[0]; B[:, [1, 4]] = B[:, [1, 4]] * RY + lo[1]; B[:, [2, 5]] = B[:, [2, 5]] * R + lo[2]
B = np.round(B, 2)
print('boîtes', len(B))

# --- escaliers : la voxélisation épaissit les murs et noie les marches. On retire les boîtes dans chaque cage d'escalier
# et sur son palier, puis on pose des marches exactes, mesurées sur les girons en béton du modèle.
Tall = P[IDX]
nrm = np.cross(Tall[:, 1] - Tall[:, 0], Tall[:, 2] - Tall[:, 0])
up = nrm[:, 1] / (np.linalg.norm(nrm, axis=1) + 1e-12) > .9
cen = Tall.mean(1)
mtl = np.array(names)[MAT[IDX[:, 0]]]
def carve(B, v):
    """soustrait la boîte v de chaque boîte de B (découpe en morceaux)"""
    out = []
    for b in B:
        if not all(b[a] < v[a + 3] and b[a + 3] > v[a] for a in range(3)):
            out.append(b); continue
        b = list(b)
        for a in range(3):
            if b[a] < v[a]:
                piece = list(b); piece[a + 3] = v[a]; out.append(piece); b[a] = v[a]
            if b[a + 3] > v[a + 3]:
                piece = list(b); piece[a] = v[a + 3]; out.append(piece); b[a + 3] = v[a + 3]
    return out
STAIRS = [  # zone de recherche des girons, volume dégagé (cage + palier)
    ((13.8, 16.2, -10.2, -6.0), (14.3, .05, -9.7, 15.65, 6.75, -5.82)),
    ((0, 0, 0, 0), (14.3, .05, -6.42, 17.4, 3.0, -5.76)),    # palier du bas de l'escalier A (mur épaissi par la voxélisation)
    ((0, 0, 0, 0), (14.3, 3.45, -6.42, 17.4, 6.3, -5.76)),
    ((0, 0, 0, 0), (-24.05, .05, -4.42, -22.9, 3.0, -3.3)),   # escalier B : accès par le nord au pied de la volée (bas du garde-corps)
    ((0, 0, 0, 0), (-24.05, 3.45, -4.42, -22.9, 6.3, -3.3)),
    ((-24.2, -20.0, -6.2, -4.0), (-24.05, .05, -5.7, -20.5, 6.75, -4.35)),
]
B = B.tolist()
steps = []
for (x0, x1, z0, z1), vol in STAIRS:
    B = carve(B, vol)
    s = up & (mtl == 'Beton') & (cen[:, 0] > x0) & (cen[:, 0] < x1) & (cen[:, 2] > z0) & (cen[:, 2] < z1) & (cen[:, 1] > .1) & (cen[:, 1] < 6.85)
    Q = Tall[s]; ys = np.round(Q[:, :, 1].mean(1), 2)
    for y in sorted(set(ys)):
        q = Q[ys == y].reshape(-1, 3)
        lo_, hi_ = q.min(0), q.max(0)
        if (hi_[0] - lo_[0]) * (hi_[2] - lo_[2]) > 3:   # dalle d'étage, pas une marche
            continue
        thin = (hi_[0] - lo_[0]) < .35 or (hi_[2] - lo_[2]) < .35
        if thin and min(hi_[0] - lo_[0], hi_[2] - lo_[2]) < .3 and max(hi_[0] - lo_[0], hi_[2] - lo_[2]) > 1.3:   # dessus de mur ou de garde-corps : plein jusqu'au sol de l'étage
            base = 3.2 if y > 3.4 else 0
            steps.append([round(lo_[0], 2), base, round(lo_[2], 2), round(hi_[0], 2), y, round(hi_[2], 2)]); continue
        # marche : une volée par étage, l'une au-dessus de l'autre ; on garde 45 cm d'épaisseur pour laisser passer la tête dessous
        steps.append([round(lo_[0], 2), max(0 if y < 3.4 else 3.2, y - .45), round(lo_[2], 2), round(hi_[0], 2), y, round(hi_[2], 2)])
B = B + steps
B = np.array(B)
print('escaliers : marches', len(steps), '— boîtes', len(B))

# apparitions : colonnes libres (0 à 2 m) au sol, dans la zone de navigation des bots (±38 m)
def free(x, z, y0=0.1, y1=2.0, r=.45):
    i0, i1 = int((x - r - lo[0]) / R), int((x + r - lo[0]) / R) + 1
    k0, k1 = int((z - r - lo[2]) / R), int((z + r - lo[2]) / R) + 1
    j0, j1 = int((y0 - lo[1]) / RY), int((y1 - lo[1]) / RY) + 1
    return not G[i0:i1, j0:j1, k0:k1].any()
cand = [(x, z) for x in range(-36, 37, 3) for z in range(-38, 37, 3) if free(x, z)]
WINGS = [(-24, 26, -6, 6), (14, 26, -30, 6)]  # ailes du bâtiment en L (x0, x1, z0, z1)
inb = lambda x, z, m=0: any(a + m < x < b - m and c + m < z < d - m for a, b, c, d in WINGS)
inside = [(x, z) for x, z in cand if inb(x, z, 1)]
outside = [(x, z) for x, z in cand if not inb(x, z, -2)]
rng = np.random.default_rng(7)
def spread(L, n):
    L = list(L); out = []
    if not L: return out
    out.append(L[rng.integers(len(L))])
    while len(out) < n and len(out) < len(L):
        d = [min((a - x) ** 2 + (b - z) ** 2 for x, z in out) for a, b in L]
        out.append(L[int(np.argmax(d))])
    return out
spawns = spread(inside, 8) + spread(outside, 10)

# lumières : grille dans le bâtiment, à chaque étage, là où le plafond est libre
lights = []
for fy in (0.0, 3.4, 6.8):
    for x in range(-21, 26, 6):
        for z in range(-27, 5, 6):
            if inb(x, z, .5) and free(x, z, fy + .3, fy + 2.7, .3):
                lights.append([x, round(fy + 2.75, 2), z, 7])
lights.append([0, 3.8, 9.8, 6])  # enseigne rouge de l'entrée
json.dump({'boxes': B.tolist(), 'spawns': spawns, 'lights': lights}, open(outjson, 'w'))
print('apparitions', len(spawns), 'lumières', len(lights))
