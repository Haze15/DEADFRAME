#!/usr/bin/env python3
"""Convertit des .glb (Sketchfab) vers le format compact .dfm du moteur DEADFRAME.

  statique : sommets cuits en espace monde, décimation par regroupement de sommets, 1 texture JPEG / matériau
  skinné   : sommets + joints/poids, squelette, animations rééchantillonnées à 30 i/s

Fichier .dfm = [u32 longueur JSON][JSON][padding 4][binaire float32/uint32]
"""
import io, json, struct, sys, os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class GLB:
    def __init__(self, path):
        d = open(path, 'rb').read()
        n = struct.unpack_from('<I', d, 12)[0]
        self.j = json.loads(d[20:20 + n])
        self.bin = memoryview(d)[20 + n + 8:]

    def view(self, i):
        v = self.j['bufferViews'][i]
        o = v.get('byteOffset', 0)
        return self.bin[o:o + v['byteLength']], v.get('byteStride', 0)

    def acc(self, i):
        a = self.j['accessors'][i]
        dt, nc = np.dtype(CT[a['componentType']]), NC[a['type']]
        buf, stride = self.view(a['bufferView'])
        off, cnt = a.get('byteOffset', 0), a['count']
        if stride and stride != dt.itemsize * nc:
            raw = np.frombuffer(buf, np.uint8, offset=off)[:stride * (cnt - 1) + dt.itemsize * nc]
            idx = (np.arange(cnt)[:, None] * stride + np.arange(dt.itemsize * nc)[None, :]).ravel()
            arr = raw[idx].view(dt).reshape(cnt, nc)
        else:
            arr = np.frombuffer(buf, dt, cnt * nc, off).reshape(cnt, nc)
        if a.get('normalized') and dt.kind in 'ui':
            arr = arr.astype(np.float32) / np.iinfo(dt).max
        return arr

    def image(self, i):
        im = self.j['images'][i]
        buf, _ = self.view(im['bufferView'])
        return Image.open(io.BytesIO(bytes(buf)))


def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def trs_m(t, r, s):
    m = np.eye(4)
    m[:3, :3] = q2m(r) * np.asarray(s)[None, :]
    m[:3, 3] = t
    return m


def node_local(n):
    if 'matrix' in n:
        return np.array(n['matrix'], float).reshape(4, 4).T
    return trs_m(n.get('translation', [0, 0, 0]), n.get('rotation', [0, 0, 0, 1]), n.get('scale', [1, 1, 1]))


def m2q(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1) * 2
        return [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, .25 * s]
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = np.sqrt(max(1e-12, 1 + R[i, i] - R[j, j] - R[k, k])) * 2
    q = [0, 0, 0, 0]
    q[i] = .25 * s
    q[j] = (R[j, i] + R[i, j]) / s
    q[k] = (R[k, i] + R[i, k]) / s
    q[3] = (R[k, j] - R[j, k]) / s
    return q


def node_trs(n):
    if 'matrix' in n:
        m = node_local(n)
        s = np.linalg.norm(m[:3, :3], axis=0)
        return list(m[:3, 3]), m2q(m[:3, :3] / s), list(s)
    return n.get('translation', [0, 0, 0]), n.get('rotation', [0, 0, 0, 1]), n.get('scale', [1, 1, 1])


def world_mats(g):
    nodes = g.j['nodes']
    W, parent = [None] * len(nodes), [-1] * len(nodes)

    def rec(i, M, p):
        W[i] = M @ node_local(nodes[i])
        parent[i] = p
        for c in nodes[i].get('children', []):
            rec(c, W[i], i)
    for r in g.j['scenes'][g.j.get('scene', 0)]['nodes']:
        rec(r, np.eye(4), -1)
    return W, parent


def base_tex(g, mat):
    """(index image couleur, facteur couleur)"""
    pbr = mat.get('pbrMetallicRoughness', {})
    sg = mat.get('extensions', {}).get('KHR_materials_pbrSpecularGlossiness', {})
    tex = pbr.get('baseColorTexture') or sg.get('diffuseTexture')
    col = pbr.get('baseColorFactor') or sg.get('diffuseFactor') or [1, 1, 1, 1]
    img = g.j['textures'][tex['index']].get('source') if tex else None
    return img, col


def export_textures(g, mats_used, name, outdir, size, quality=84):
    out = []
    cache = {}
    for mi in mats_used:
        mat = g.j['materials'][mi] if mi is not None else {}
        img, col = base_tex(g, mat)
        fn = None
        if img is not None:
            if img not in cache:
                im = g.image(img).convert('RGB')
                if max(im.size) > size:
                    im.thumbnail((size, size), Image.LANCZOS)
                fn = f'{name}_{len(cache)}.jpg'
                im.save(f'{outdir}/{fn}', 'JPEG', quality=quality, optimize=True)
                cache[img] = fn
            fn = cache[img]
        out.append({'name': mat.get('name', ''), 'tex': fn, 'color': [round(float(c), 4) for c in col[:3]],
                    'blend': mat.get('alphaMode') == 'BLEND', 'twoSided': bool(mat.get('doubleSided'))})
    return out


def write_dfm(path, meta, chunks):
    off, blobs = 0, []
    for key, arr in chunks:
        b = np.ascontiguousarray(arr).tobytes()
        b += b'\0' * (-len(b) % 4)
        meta[key] = [off, arr.size]
        off += len(b)
        blobs.append(b)
    js = json.dumps(meta, separators=(',', ':')).encode()
    js += b' ' * (-(4 + len(js)) % 4)
    with open(path, 'wb') as f:
        f.write(struct.pack('<I', len(js)) + js + b''.join(blobs))
    return 4 + len(js) + off


def cluster(P, N, UV, MAT, IDX, cell, uvq=24):
    """Décimation par regroupement : positions = barycentre de cellule, attributs par (cellule, matériau, zone UV)."""
    mn = P.min(0)
    q = np.floor((P - mn) / cell).astype(np.int64)
    K = int(q.max()) + 2
    sp_key = q[:, 0] + q[:, 1] * K + q[:, 2] * K * K
    _, sp = np.unique(sp_key, return_inverse=True)
    ns = sp.max() + 1
    cnt = np.bincount(sp, minlength=ns).astype(np.float64)
    C = np.stack([np.bincount(sp, P[:, k], ns) / cnt for k in range(3)], 1)
    uvc = (np.floor(UV[:, 0] * uvq).astype(np.int64) % 4096) * 4096 + (np.floor(UV[:, 1] * uvq).astype(np.int64) % 4096)
    key = (sp.astype(np.int64) * 64 + MAT) * (1 << 24) + uvc
    _, first, inv = np.unique(key, return_index=True, return_inverse=True)
    nv = len(first)
    Nn = np.stack([np.bincount(inv, N[:, k], nv) for k in range(3)], 1)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)
    tri_sp = sp[IDX]
    ok = (tri_sp[:, 0] != tri_sp[:, 1]) & (tri_sp[:, 1] != tri_sp[:, 2]) & (tri_sp[:, 0] != tri_sp[:, 2])
    T = inv[IDX[ok]]
    ts = np.sort(tri_sp[ok], 1)
    tk = (ts[:, 0] * ns + ts[:, 1]) * ns + ts[:, 2]
    _, keep = np.unique(tk, return_index=True)
    T = T[np.sort(keep)]
    used = np.unique(T)
    remap = np.full(nv, -1, np.int64)
    remap[used] = np.arange(len(used))
    f = first[used]
    return C[sp[f]], Nn[used], UV[f], MAT[f], remap[T]


def gather_static(g, skip_mats=()):
    W, _ = world_mats(g)
    Ps, Ns, UVs, Ms, Is, off = [], [], [], [], [], 0
    mats = []
    for ni, n in enumerate(g.j['nodes']):
        if 'mesh' not in n or W[ni] is None:
            continue
        M = W[ni]
        NM = np.linalg.inv(M[:3, :3]).T
        for p in g.j['meshes'][n['mesh']]['primitives']:
            if p.get('mode', 4) != 4:
                continue
            mi = p.get('material')
            mname = g.j['materials'][mi].get('name', '') if mi is not None else ''
            if mname in skip_mats:
                continue
            if mi not in mats:
                mats.append(mi)
            a = p['attributes']
            P = g.acc(a['POSITION']).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
            N = g.acc(a['NORMAL']).astype(np.float64) @ NM.T if 'NORMAL' in a else np.tile([0, 1, 0.], (len(P), 1))
            UV = g.acc(a['TEXCOORD_0']).astype(np.float64) if 'TEXCOORD_0' in a else np.zeros((len(P), 2))
            I = g.acc(p['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in p else np.arange(len(P)).reshape(-1, 3)
            if np.linalg.det(M[:3, :3]) < 0:
                I = I[:, ::-1]
            Ps.append(P); Ns.append(N); UVs.append(UV); Ms.append(np.full(len(P), mats.index(mi), np.int64)); Is.append(I + off)
            off += len(P)
    return np.concatenate(Ps), np.concatenate(Ns), np.concatenate(UVs), np.concatenate(Ms), np.concatenate(Is), mats


def pack_prims(P, N, UV, MAT, IDX, extra=None):
    """Trie les triangles par matériau -> (vertex buffer, index buffer, prims)."""
    tm = MAT[IDX[:, 0]]
    order = np.argsort(tm, kind='stable')
    IDX, tm = IDX[order], tm[order]
    prims = []
    for m in np.unique(tm):
        w = np.nonzero(tm == m)[0]
        prims.append({'mat': int(m), 'first': int(w[0] * 3), 'count': int(len(w) * 3)})
    cols = [P, N, UV] + ([extra] if extra is not None else [])
    V = np.concatenate(cols, 1).astype(np.float32)
    return V, IDX.astype(np.uint32).ravel(), prims


def soldier_rig(P):
    """Squelette procédural (le modèle n'en a pas) : poids calculés d'après la position, pose en A.
    Os : 0 bassin, 1 buste, 2 tête, 3/4 bras G haut/avant, 5/6 bras D, 7/8 jambe G cuisse/tibia, 9/10 jambe D."""
    x, y = P[:, 0], P[:, 1]
    ax, n = np.abs(x), len(P)
    def ss(a, b, v):
        t = np.clip((v - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    side = (x > 0).astype(int)
    J = np.zeros((n, 4)); W = np.zeros((n, 4))
    c = ss(1.0, 1.2, y)
    J[:, 0] = 1; W[:, 0] = c; W[:, 1] = 1 - c
    h = ss(1.50, 1.58, y) * (ax < .17)
    m = h > 0
    J[m, 0] = 2; J[m, 1] = 1; W[m, 0] = h[m]; W[m, 1] = 1 - h[m]
    s_, t_ = ss(.80, .95, y), ss(.53, .41, y)
    thigh, shin = 7 + 2 * side, 8 + 2 * side
    m = (y < .95) & (y >= .6)
    J[m, 0] = thigh[m]; J[m, 1] = 0; W[m, 0] = 1 - s_[m]; W[m, 1] = s_[m]
    m = y < .6
    J[m, 0] = shin[m]; J[m, 1] = thigh[m]; W[m, 0] = t_[m]; W[m, 1] = 1 - t_[m]
    inner = np.where(y < 1.3, .29, .29 - (y - 1.3) * .2)
    a = ss(-.05, .05, ax - inner)
    hand = (y < .98) & (ax > .31)
    a = np.where(hand, 1., np.where(y < .98, 0., a))
    a = np.where((y > .70) & (y < 1.53), a, 0.)
    e = ss(1.18, 1.06, y)
    m = a > 0
    body = np.where(c > .5, 1, 0)
    J[m, 0] = (4 + 2 * side)[m]; J[m, 1] = (3 + 2 * side)[m]; J[m, 2] = body[m]; J[m, 3] = 0
    W[m, 0] = (a * e)[m]; W[m, 1] = (a * (1 - e))[m]; W[m, 2] = (1 - a)[m]; W[m, 3] = 0
    return np.concatenate([J, W / W.sum(1, keepdims=True)], 1)


def convert_static(src, name, outdir, target, tex=1024, fix=None, skip_mats=(), lods=(), cut=None, rig=None):
    g = GLB(src)
    P, N, UV, MAT, IDX, mats = gather_static(g, skip_mats)
    if cut is not None:  # supprime les triangles dans une boîte (espace d'origine)
        inb = np.all((P >= np.array(cut[0])) & (P <= np.array(cut[1])), 1)
        IDX = IDX[~inb[IDX].any(1)]
    if fix is not None:  # matrice 4x4 : espace modèle -> espace jeu (mètres, -Z = avant, Y = haut)
        F = np.asarray(fix, float)
        P = P @ F[:3, :3].T + F[:3, 3]
        N = N @ np.linalg.inv(F[:3, :3]).T.T
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    res = []
    for suffix, tgt in [('', target)] + list(lods):
        p, n, uv, mat, idx = P, N, UV, MAT, IDX
        if len(IDX) > tgt:
            diag = np.linalg.norm(P.max(0) - P.min(0))
            lo, hi = diag / 4000, diag / 8
            for _ in range(18):
                mid = (lo * hi) ** .5
                r = cluster(P, N, UV, MAT, IDX, mid)
                if len(r[4]) > tgt:
                    lo = mid
                else:
                    hi = mid; p, n, uv, mat, idx = r
        V, I, prims = pack_prims(p, n, uv, mat, idx, rig(p) if rig else None)
        meta = {'skinned': bool(rig), 'stride': 16 if rig else 8, 'rig': 11 if rig else 0, 'prims': prims, 'bbox': [p.min(0).round(4).tolist(), p.max(0).round(4).tolist()],
                'mats': export_textures(g, mats, name, outdir, tex) if suffix == '' else res[0][1]['mats'],
                'credit': g.j['asset'].get('extras', {})}
        sz = write_dfm(f'{outdir}/{name}{suffix}.dfm', meta, [('vtx', V), ('idx', I)])
        res.append((suffix, meta))
        print(f'{name}{suffix}: {len(IDX)} -> {len(idx)} tris, {len(V)} verts, {sz//1024} KB, bbox {meta["bbox"]}')
    return res


def convert_skinned(src, name, outdir, tex=1024, fps=30, skip_mats=(), only_anims=None, pos_fix=None, bake=None):
    g = GLB(src)
    j = g.j
    nodes = j['nodes']
    W, parent = world_mats(g)
    skin = j['skins'][0]
    joints = skin['joints']
    ibm = g.acc(skin['inverseBindMatrices']).astype(np.float32)  # (n,16) column-major
    Ps, Ns, UVs, Ms, Is, Js, Ws, off, mats = [], [], [], [], [], [], [], 0, []
    for n in nodes:
        if 'mesh' not in n or 'skin' not in n:
            continue
        for p in j['meshes'][n['mesh']]['primitives']:
            mi = p.get('material')
            if j['materials'][mi].get('name', '') in skip_mats:
                continue
            if mi not in mats:
                mats.append(mi)
            a = p['attributes']
            P = g.acc(a['POSITION']).astype(np.float64)
            if pos_fix and np.abs(P).max() > pos_fix[0]:
                P = P * pos_fix[1]
            Ps.append(P); Ns.append(g.acc(a['NORMAL']).astype(np.float64))
            UVs.append(g.acc(a['TEXCOORD_0']).astype(np.float64) if 'TEXCOORD_0' in a else np.zeros((len(P), 2)))
            Js.append(g.acc(a['JOINTS_0']).astype(np.float64)); w = g.acc(a['WEIGHTS_0']).astype(np.float64)
            Ws.append(w / np.maximum(w.sum(1, keepdims=True), 1e-9))
            Ms.append(np.full(len(P), mats.index(mi), np.int64))
            Is.append(g.acc(p['indices']).astype(np.int64).reshape(-1, 3) + off); off += len(P)
    P, N, UV, MAT, IDX = map(np.concatenate, (Ps, Ns, UVs, Ms, Is))
    V, I, prims = pack_prims(P, N, UV, MAT, IDX, np.concatenate([np.concatenate(Js), np.concatenate(Ws)], 1))
    rest = np.array([np.concatenate(node_trs(n)) for n in nodes], np.float32)  # (nodes,10) T R S
    chunks = [('vtx', V), ('idx', I), ('ibm', ibm), ('rest', rest)]
    anims = []
    for ai, an in enumerate(j.get('animations', [])):
        nm = an.get('name', f'anim{ai}').split('|')[-1]
        if only_anims and nm not in only_anims:
            continue
        tmax = max(float(j['accessors'][s['input']]['max'][0]) for s in an['samplers'])
        nf = max(2, int(round(tmax * fps)) + 1)
        ts = np.arange(nf) / fps
        an_nodes = sorted(set(c['target']['node'] for c in an['channels'] if 'node' in c['target']))
        data = np.repeat(rest[an_nodes][None], nf, 0).astype(np.float64)  # (nf, n, 10)
        for c in an['channels']:
            s = an['samplers'][c['sampler']]
            tin = g.acc(s['input']).astype(np.float64).ravel()
            val = g.acc(s['output']).astype(np.float64)
            if s.get('interpolation') == 'CUBICSPLINE':
                val = val[1::3]
            k = an_nodes.index(c['target']['node'])
            path = c['target']['path']
            if path == 'rotation':
                for i in range(1, len(val)):
                    if np.dot(val[i], val[i - 1]) < 0:
                        val[i] = -val[i]
            if s.get('interpolation') == 'STEP':
                ii = np.clip(np.searchsorted(tin, ts, 'right') - 1, 0, len(tin) - 1)
                out = val[ii]
            else:
                out = np.stack([np.interp(ts, tin, val[:, d]) for d in range(val.shape[1])], 1)
            if path == 'translation':
                data[:, k, 0:3] = out
            elif path == 'rotation':
                data[:, k, 3:7] = out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)
            elif path == 'scale':
                data[:, k, 7:10] = out
        key = f'anim{len(anims)}'
        chunks.append((key, data.astype(np.float32)))
        anims.append({'name': nm, 'fps': fps, 'frames': nf, 'nodes': an_nodes, 'key': key})
    # boîte englobante skinnée (pose de la 1re image de la 1re anim) — pour le cadrage
    def pose_world(frame_data, an_nodes):
        loc = rest.astype(np.float64).copy()
        if an_nodes is not None:
            loc[an_nodes] = frame_data
        Wm = [None] * len(nodes)
        order = [i for i in range(len(nodes)) if parent[i] == -1]
        for i in order:
            pm = np.eye(4) if parent[i] == -1 else Wm[parent[i]]
            Wm[i] = pm @ trs_m(loc[i, 0:3], loc[i, 3:7], loc[i, 7:10])
            order.extend(nodes[i].get('children', []))
        return Wm
    Wm = pose_world(None, None)
    if anims:
        d0 = np.frombuffer(np.ascontiguousarray(dict(chunks)[anims[0]['key']]).tobytes(), np.float32).reshape(anims[0]['frames'], -1, 10)
        Wm = pose_world(d0[0], anims[0]['nodes'])
    JM = np.stack([Wm[jn] @ ibm[k].reshape(4, 4).T.astype(np.float64) for k, jn in enumerate(joints)])
    Jidx, Wt = V[:, 8:12].astype(int), V[:, 12:16].astype(np.float64)
    Ph = np.concatenate([P, np.ones((len(P), 1))], 1)
    SP = sum(Wt[:, k:k + 1] * np.einsum('nij,nj->ni', JM[Jidx[:, k]], Ph) for k in range(4))[:, :3]
    if bake is not None:  # fige la pose 0 -> modèle statique (ex. AKM : seul le fusil est exploitable)
        SN = sum(Wt[:, k:k + 1] * np.einsum('nij,nj->ni', JM[Jidx[:, k]][:, :3, :3], N) for k in range(4))
        SN /= np.maximum(np.linalg.norm(SN, axis=1, keepdims=True), 1e-9)
        keep = [m for m, mi in enumerate(mats) if j['materials'][mi].get('name') in bake['keep']]
        tri = IDX[np.isin(MAT[IDX[:, 0]], keep)]
        dom = np.array([nodes[joints[k]].get('name', '') for k in Jidx[np.arange(len(P)), Wt.argmax(1)]])
        for pre in bake.get('drop_joints', ()):
            tri = tri[~np.char.startswith(dom[tri[:, 0]], pre)]
        used = np.unique(tri); remap = np.full(len(P), -1); remap[used] = np.arange(len(used))
        F = np.asarray(bake.get('fix', np.eye(4)), float)
        p2 = SP[used] @ F[:3, :3].T + F[:3, 3]
        n2 = SN[used] @ np.linalg.inv(F[:3, :3]); n2 /= np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-9)
        V2, I2, prims2 = pack_prims(p2, n2, UV[used], MAT[used], remap[tri])
        meta = {'skinned': False, 'stride': 8, 'prims': prims2, 'bbox': [p2.min(0).round(4).tolist(), p2.max(0).round(4).tolist()],
                'mats': export_textures(g, mats, name, outdir, tex), 'credit': j['asset'].get('extras', {})}
        sz = write_dfm(f'{outdir}/{name}.dfm', meta, [('vtx', V2), ('idx', I2)])
        print(f'{name} (pose figée): {len(tri)} tris, {sz//1024} KB, bbox {meta["bbox"]}')
        return meta
    meta = {'skinned': True, 'stride': 16, 'prims': prims, 'bbox': [SP.min(0).round(4).tolist(), SP.max(0).round(4).tolist()],
            'mats': export_textures(g, mats, name, outdir, tex), 'parents': parent, 'joints': joints,
            'nodeNames': [n.get('name', '') for n in nodes], 'anims': anims, 'credit': j['asset'].get('extras', {})}
    for m in range(len(mats)):
        w = MAT == m
        meta['mats'][m]['bbox'] = [SP[w].min(0).round(3).tolist(), SP[w].max(0).round(3).tolist()]
    sz = write_dfm(f'{outdir}/{name}.dfm', meta, chunks)
    print(f'{name}: {len(IDX)} tris, {len(V)} verts, {len(joints)} joints, anims {[(a["name"], a["frames"]) for a in anims]}, {sz//1024} KB')
    print('  bbox pose0', meta['bbox'])
    for m in meta['mats']:
        print('   mat', m['name'], m['tex'], m['blend'], m['bbox'])
    return meta


if __name__ == '__main__':
    U = '/mnt/user-data/uploads/'
    out = sys.argv[1]
    which = sys.argv[2:] or ['soldier', 'pistol', 'hk416', 'aks74', 'akm']
    os.makedirs(out, exist_ok=True)
    if 'soldier' in which:
        S = 1.8 / .98
        convert_static(U + '40bcf9f8-modern_tactical_soldier.glb', 'soldier', out, 36000, 1024,
                       fix=[[0, 0, S, 0], [0, S, 0, .49 * S], [-S, 0, 0, 0], [0, 0, 0, 1]], rig=soldier_rig)  # face à -Z, pieds à y=0, 1,80 m
    if 'pistol' in which:
        convert_static(U + 'ccae6623-pistol_43_tactical__free_lowpoly.glb', 'pistol', out, 99999, 1024)
    if 'hk416' in which:
        convert_static(U + 'hk416_full_reworked.glb', 'hk416', out, 110000, 1024, lods=[('_lod', 3500)], skip_mats=('Glass',),
                       cut=([-1, .0298, .0105], [1, 1, .0278]))  # retire la hausse rabattable qui masquait le viseur holographique
    if 'aks74' in which:
        convert_skinned(U + '817a8f72-stalker_aks-74_reanimation.glb', 'aks74', out, 1024, skip_mats=('wpn_upgrade_S', 'wpn_vog_S'))
    if 'akm' in which:
        convert_skinned(U + 'akm_reload_animation.glb', 'akm', out, 1024, bake={'keep': ('AK_mat',), 'drop_joints': ('mag2',)})
