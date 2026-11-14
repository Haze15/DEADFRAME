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
