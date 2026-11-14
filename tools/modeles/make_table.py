"""Table en bois low poly -> table.glb (glTF 2.0, une texture bois procédurale embarquée)."""
import json, struct, io, numpy as np
from PIL import Image, ImageFilter

# ---------- texture bois 512x512 (veines le long de U)
rng = np.random.default_rng(7); S = 512
v = np.linspace(0, 1, S)[:, None]; u = np.linspace(0, 1, S)[None, :]
warp = sum(np.sin(2*np.pi*(f*u + rng.random()))*a for f, a in [(1, .05), (3, .02), (7, .008)])
rings = np.sin((v + warp) * 2*np.pi * 18 + np.sin(u*2*np.pi*2)*1.5)
grain = rng.normal(0, 1, (S, S)); grain = np.array(Image.fromarray(((grain*30)+128).clip(0,255).astype(np.uint8)).resize((S//16, S)).resize((S, S)), float)/255-.5
t = (.55 + .18*rings + .25*grain).clip(0, 1)
light, dark = np.array([.62, .44, .26]), np.array([.30, .19, .10])
img = (dark + (light-dark)*t[..., None])
planks = ((v*4) % 1 < .012).astype(float)[..., None]   # joints de planches
img = img*(1-.55*planks)
im = Image.fromarray((img*255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.SMOOTH)
buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True); png = buf.getvalue(); im.save('tools/modeles/wood.png')

# ---------- géométrie : pavés avec UV à densité constante (1 m = 1 tour de texture)
P, N, UV, I = [], [], [], []
def cube(x0, y0, z0, x1, y1, z1, grain_axis=0):
    faces = [((0, 0, -1), [(x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)]),
             ((0, 0, 1),  [(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]),
             ((-1, 0, 0), [(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)]),
             ((1, 0, 0),  [(x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)]),
             ((0, 1, 0),  [(x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)]),
             ((0, -1, 0), [(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)])]
    for n, q in faces:
        b = len(P); ax = [a for a in range(3) if n[a] == 0]
        # U suit l'axe du fil du bois si présent sur la face, sinon le premier axe libre
        ua = grain_axis if grain_axis in ax else ax[0]; va = [a for a in ax if a != ua][0]
        for p in q:
            P.append(p); N.append(n); UV.append((p[ua]*.9 + .37*grain_axis, p[va]*.9))
        I.extend([b, b+1, b+2, b, b+2, b+3])

W, D, H, T = 1.60, 0.90, 0.76, 0.05          # largeur, profondeur, hauteur, épaisseur du plateau
L, inset, ah = 0.07, 0.06, 0.09              # section des pieds, retrait, hauteur des ceintures
hw, hd = W/2, D/2
cube(-hw, H-T, -hd, hw, H, hd, 0)                                   # plateau
for sx in (-1, 1):
    for sz in (-1, 1):
        cx, cz = sx*(hw-inset-L/2), sz*(hd-inset-L/2)
        cube(cx-L/2, 0, cz-L/2, cx+L/2, H-T, cz+L/2, 1)             # pieds (fil vertical)
ex, ez = hw-inset-L/2, hd-inset-L/2
for sz in (-1, 1): cube(-ex, H-T-ah, sz*ez-.012, ex, H-T, sz*ez+.012, 0)   # ceintures longues
for sx in (-1, 1): cube(sx*ex-.012, H-T-ah, -ez, sx*ex+.012, H-T, ez, 2)   # ceintures courtes
for sx in (-1, 1): cube(sx*ex-.015, .12, -ez, sx*ex+.015, .16, ez, 2)      # entretoises basses
cube(-ex, .12, -.015, ex, .16, .015, 0)                                     # traverse centrale

P = np.array(P, np.float32); N = np.array(N, np.float32); UV = np.array(UV, np.float32); I = np.array(I, np.uint16)

# ---------- assemblage GLB
chunks, views, accs = b'', [], []
def add(data, target=None):
    global chunks
    off = len(chunks); chunks += data
    while len(chunks) % 4: chunks += b'\0'
    v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
    if target: v['target'] = target
    views.append(v); return len(views)-1
def acc(arr, typ, ctype, target):
    a = {'bufferView': add(arr.tobytes(), target), 'componentType': ctype, 'count': len(arr), 'type': typ}
    if typ == 'VEC3': a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    accs.append(a); return len(accs)-1
pa = acc(P, 'VEC3', 5126, 34962); na = acc(N, 'VEC3', 5126, 34962); ua = acc(UV, 'VEC2', 5126, 34962); ia = acc(I, 'SCALAR', 5123, 34963)
img_view = add(png)
gltf = {'asset': {'version': '2.0', 'generator': 'DEADFRAME make_table.py'},
        'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': 'Table', 'mesh': 0}],
        'meshes': [{'name': 'Table', 'primitives': [{'attributes': {'POSITION': pa, 'NORMAL': na, 'TEXCOORD_0': ua}, 'indices': ia, 'material': 0}]}],
        'materials': [{'name': 'Bois', 'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}, 'metallicFactor': 0, 'roughnessFactor': .8}}],
        'textures': [{'source': 0, 'sampler': 0}], 'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
        'images': [{'bufferView': img_view, 'mimeType': 'image/png'}],
        'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(chunks)}]}
js = json.dumps(gltf, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
glb = struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(chunks)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(chunks), 0x004E4942) + chunks
open('tools/modeles/table.glb', 'wb').write(glb)
print(f'table.glb : {len(glb)//1024} Ko, {len(I)//3} triangles, {len(P)} sommets, {W}x{D}x{H} m')
