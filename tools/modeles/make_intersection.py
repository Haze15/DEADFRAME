"""Intersections de tranchées -> tranchee_croisement.glb (X), tranchee_T_droite.glb, tranchee_T_gauche.glb
Tuile de 8 x 8 m centrée en (0,0). Axe nord-sud = ligne droite standard (entrée z=+4, sortie z=-4, parapet côté -X).
Branche ouest : sortie en x=-4 (comme le virage gauche, parapet côté +Z). Branche est : sortie en x=+4, parapet côté +Z
(on y entre en marchant vers -X : une ligne droite tournée de +90° centrée en (+8,0) s'y raccorde, comme en (-8,0) à l'ouest)."""
import math, numpy as np
exec(open('tools/modeles/make_trench.py').read().split("\nD = '")[0])
B = DEPTH+.05
HP = [(px, py) for px, py in PROF]
HP = [(-HALF_W-.065, 1.85) if (px, py) == (-HALF_W-.06, 1.85) else (HALF_W+.065, 1.85) if (px, py) == (HALF_W+.06, 1.85) else (px, py) for px, py in HP]
HX = np.array([p[0] for p in HP]); HY = np.array([p[1] for p in HP])
prof = lambda lat: np.interp(lat, HX, HY)
WALL = HALF_W+.06

def build_x(arms, out):
    global G, rng
    rng = np.random.default_rng(14); G = {k: ([], [], [], []) for k in TEX}
    E, W = 'E' in arms, 'W' in arms
    def height(x, z):
        a = prof(x)-B; b = prof(-z)-B                      # nord-sud : latéral = x ; est-ouest (vers -X) : latéral = -z
        if not (E and W): b = np.where((x > 0) if E else (x < 0), b, 0.0)
        s = lambda v: np.clip(1+v/.3, 0, 1)
        return B + np.minimum(np.minimum(a, 0), np.minimum(b, 0)) + np.maximum(a, 0)*s(b) + np.maximum(b, 0)*s(a)
    # --- terre : grille dont les lignes passent par toutes les cassures du profil
    lin = np.linspace(-4, 4, 33)
    xs = np.unique(np.round(np.concatenate([lin, HX[np.abs(HX) <= 4]]), 4))
    zs = np.unique(np.round(np.concatenate([lin, -HX[np.abs(HX) <= 4]]), 4))
    X, Z = np.meshgrid(xs, zs); Y = height(X, Z)
    env = np.sin(math.pi*(X+4)/8)*np.sin(math.pi*(Z+4)/8)
    ax, az = np.abs(X), np.abs(Z)
    out_ns = ax > 1.0; out_ew = (az > 1.0) | ((X <= 0) if (E and not W) else (X >= 0) if (W and not E) else False)
    mask = (out_ns & out_ew).astype(float)
    Y = Y + rng.normal(0, .07, Y.shape)*env*mask
    floor = (Y < .06).astype(float); Y = Y + rng.normal(0, .02, Y.shape)*env*floor
    nx, nz = len(xs), len(zs); P, UV, I = [], [], []
    for j in range(nz):
        for i in range(nx): P.append((X[j, i], Y[j, i], Z[j, i])); UV.append((X[j, i]*.5, Z[j, i]*.5))
    for j in range(nz-1):
        for i in range(nx-1):
            a, b, c, d = j*nx+i, j*nx+i+1, (j+1)*nx+i, (j+1)*nx+i+1
            I += [a, c, b, b, c, d]
    tri_mesh('Terre', P, UV, I)
    H = lambda x, z: float(height(np.array(x), np.array(z)))

    # --- coffrage : murs (axe, position, de, à), coupés aux branches
    xw = HALF_W+.035; walls = []
    for s in (-1, 1):
        gap = (W if s < 0 else E)
        walls += [('z', s*xw, 4, WALL-.02), ('z', s*xw, -WALL+.02, -4)] if gap else [('z', s*xw, 4, -4)]
    for side, on in (('E', E), ('W', W)):
        if not on: continue
        sg = 1 if side == 'E' else -1
        for s in (-1, 1): walls.append(('x', s*xw, sg*4, sg*(WALL-.02)))
    for axis, c, a0, a1 in walls:
        L = abs(a1-a0); n = max(1, math.ceil(L/2.0-1e-6)); d = 1 if a1 > a0 else -1
        for p in range(n):
            t0, t1 = a0+d*L*p/n, a0+d*L*(p+1)/n; m = (t0+t1)/2; ln = abs(t1-t0)-.01
            for row in range(8):
                yc = .14+row*.225+rng.normal(0, .008)
                if axis == 'z': box('Bois', (c, yc, m), (.035, .2, ln), .9, rng.normal(0, .004))
                else: box('Bois', (m, yc, c), (ln, .2, .035), .9, rng.normal(0, .004))
        cp = c-np.sign(c)*.055                                     # poteaux devant les planches
        for p in range(n+1):
            t = a0+d*L*p/n; t = np.clip(t, -3.94, 3.94)
            pos = (cp, .95, t) if axis == 'z' else (t, .95, cp)
            box('Bois', pos, (.12, 1.9+rng.uniform(0, .12), .12), .8, rng.normal(0, .03))
    # --- caillebotis : nord-sud sur 8 m, branches est/ouest à partir du bord du caillebotis central
    def duck(c0, c1, alongZ):
        L = abs(c1-c0); n = max(1, round(L)); ml = L/n; d = 1 if c1 > c0 else -1
        for m in range(n):
            cc = c0+d*(m+.5)*ml
            for s in (-1, 1):
                box('Bois', (s*.3, .05, cc) if alongZ else (cc, .05, s*.3), (.07, .09, ml-.02) if alongZ else (ml-.02, .09, .07), 1.2)
            k = round(ml/.168)
            for q in range(k):
                t = cc-d*ml/2+d*(q+.5)*ml/k
                box('Bois', (rng.normal(0, .01), .115, t) if alongZ else (t, .115, rng.normal(0, .01)), (.92, .04, .1) if alongZ else (.1, .04, .92), 1.2, rng.normal(0, .025))
    duck(4, -4, True)
    if E: duck(.48, 4, False)
    if W: duck(-.48, -4, False)
    # --- sacs de sable sur les parapets (posés sur la terre)
    def bags(p0, p1, lat_axis, lat_sign):
        """rangées le long d'un segment ; lat = décalage vers le parapet"""
        (x0, z0), (x1, z1) = p0, p1; L = math.hypot(x1-x0, z1-z0); dx, dz = (x1-x0)/L, (z1-z0)/L
        rot_along = math.atan2(dx, dz)
        for layer in range(3):
            off = 1.02-layer*.04; t = .29+(.29 if layer % 2 else 0)
            while t < L-.2:
                x, z = x0+dx*t, z0+dz*t
                if lat_axis == 'x': x = lat_sign*off
                else: z = lat_sign*off
                y = H(x, z)+.07+layer*.155
                sandbag((x+rng.normal(0, .02), y, z), rot=rot_along+math.pi/2+rng.normal(0, .06)); t += .58
        t = .35
        while t < L-.25:
            x, z = x0+dx*t, z0+dz*t
            if lat_axis == 'x': x = lat_sign*1.42
            else: z = lat_sign*1.42
            sandbag((x, H(x, z)+.12, z+rng.normal(0, .02)), rot=rot_along+rng.normal(0, .08)); t += .62
    if W: bags((0, 4), (0, 1.0), 'x', -1); bags((0, -1.0), (0, -4), 'x', -1)
    else: bags((0, 4), (0, -4), 'x', -1)
    if E: bags((4, 0), (1.0, 0), 'z', 1)
    if W: bags((-1.0, 0), (-4, 0), 'z', 1)
    write_glb(out)

D = 'tools/modeles/'
build_x('EW', D+'tranchee_croisement.glb')
build_x('E', D+'tranchee_T_droite.glb')
build_x('W', D+'tranchee_T_gauche.glb')
