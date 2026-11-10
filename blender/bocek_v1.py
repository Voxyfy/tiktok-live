# Karikatür hamam böceği modeli: Blender'da başsız (headless) çalışır, public/models/bocek.glb üretir.
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/bocek.py -- <çıktı.glb> [önizleme.png]
# Eklemler boş nesne (empty) zinciri: shoulder_R > elbow_R > wrist_R, hip_R > knee_R > ankle_R (L için aynı).
# Dönüşleri sıfır bırakıldı; sahne kodu (dance.js) eksenleri aynen kullanır. Yüz -Y yönüne bakar (glTF'te +Z).
# Kıyafet parçaları ayrı nesne: vest, sash, hat_fes, hat_kasket, hat_posu, hat_yemeni; sahne renklerini değiştirir.
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'bocek.glb'
PREVIEW = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def material(name, color, rough=0.5, coat=0.0, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat and 'Coat Weight' in b.inputs:
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.15
    return m

def srgb(h):  # 0xRRGGBB -> doğrusal renk
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

M = {
    'kabuk':  material('kabuk',  srgb(0x7a3b12), 0.28, 0.9),
    'koyu':   material('koyu',   srgb(0x4a2109), 0.35, 0.6),
    'kanat':  material('kanat',  srgb(0x8f4a1c), 0.2, 1.0),
    'karin':  material('karin',  srgb(0xb06a32), 0.45, 0.3),
    'goz':    material('goz',    srgb(0xf7f3ea), 0.15),
    'bebek':  material('bebek',  srgb(0x111111), 0.1),
    'iris':   material('iris',   srgb(0xc98a2b), 0.3),
    'kas':    material('kas',    srgb(0x2a1004), 0.6),
    'agiz':   material('agiz',   srgb(0x2b0a05), 0.6),
    'dis':    material('dis',    srgb(0xfafafa), 0.2),
    'vest':   material('vest',   srgb(0x222222), 0.7),
    'sash':   material('sash',   srgb(0xb5121b), 0.6),
    'hat':    material('hat',    srgb(0xb5121b), 0.6),
    'gold':   material('gold',   srgb(0xd4a017), 0.3, 0, 0.8),
}

def link(o):
    scn.collection.objects.link(o); return o

def empty(name, parent, local):
    e = link(bpy.data.objects.new(name, None)); e.empty_display_size = 0.05
    e.parent = parent; e.location = local
    return e

def world(e):
    p, v = e, Vector()
    while p: v += p.location; p = p.parent
    return v

def finish(o, mat, parent, subd=2, smooth=True):
    o.data.materials.clear(); o.data.materials.append(M[mat] if isinstance(mat, str) else mat)
    if smooth:
        for poly in o.data.polygons: poly.use_smooth = True
    if subd:
        mod = o.modifiers.new('sub', 'SUBSURF'); mod.levels = subd; mod.render_levels = subd
    if parent:
        mw = o.matrix_world.copy(); o.parent = parent; o.matrix_world = mw
    return o

def sphere(name, loc, scale, mat, parent, rot=(0, 0, 0), subd=1, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, mat, parent, subd)

def cyl(name, a, b, r0, r1, mat, parent, subd=1):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r0, radius2=r1, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return finish(o, mat, parent, subd)

def torus(name, loc, major, minor, mat, parent, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=32, minor_segments=12, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, mat, parent, 1)

def curve(name, pts, depth, mat, parent):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = depth; cu.bevel_resolution = 3
    sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = 3
    for p, c in zip(sp.points, pts): p.co = (*c, 1)
    # Uca doğru incelir
    for i, p in enumerate(sp.points): p.radius = 1 - 0.7 * i / (len(pts) - 1)
    o = link(bpy.data.objects.new(name, cu))
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    return finish(o, mat, parent, 0)

# ---------- İskelet (boş nesneler) ----------
root = link(bpy.data.objects.new('bocek', None))
body = empty('body', root, (0, 0, 0))
head = empty('head', body, (0, 0, 1.6))
J = {}
for k, s in (('R', -1), ('L', 1)):
    sh = empty(f'shoulder_{k}', body, (s * 0.3, 0, 1.28)); el = empty(f'elbow_{k}', sh, (0, 0, -0.3)); wr = empty(f'wrist_{k}', el, (0, 0, -0.28))
    hp = empty(f'hip_{k}', body, (s * 0.15, 0.05, 0.64)); kn = empty(f'knee_{k}', hp, (0, 0, -0.32)); an = empty(f'ankle_{k}', kn, (0, 0, -0.3))
    J[k] = dict(sh=sh, el=el, wr=wr, hp=hp, kn=kn, an=an, s=s)
bpy.context.view_layer.update()

# ---------- Gövde ----------
sphere('gogus', (0, 0, 1.08), (0.32, 0.25, 0.36), 'kabuk', body)
sphere('pronotum', (0, 0.05, 1.35), (0.34, 0.27, 0.09), 'kabuk', body, rot=(-0.15, 0, 0))   # omuz kalkanı
for i, (z, r) in enumerate([(0.86, 0.3), (0.76, 0.28), (0.66, 0.25), (0.57, 0.2)]):          # boğumlu karın
    sphere(f'karin{i}', (0, 0.0, z), (r, r * 0.82, 0.07), 'karin', body)
for s in (-1, 1):                                                                              # kanat kapakları
    sphere(f'kanat{s}', (s * 0.13, 0.2, 0.92), (0.17, 0.07, 0.5), 'kanat', body, rot=(-0.12, s * 0.12, 0))
    cyl(f'orta_bacak{s}', (s * 0.24, -0.1, 0.98), (s * 0.42, -0.32, 0.86), 0.025, 0.012, 'koyu', body)   # göğüste ikinci kol çifti

# ---------- Kafa ----------
H = world(head)
sphere('kafa', H + Vector((0, -0.03, 0.03)), (0.27, 0.24, 0.24), 'kabuk', head)
for s in (-1, 1):
    sphere(f'goz{s}', H + Vector((s * 0.1, -0.2, 0.09)), (0.085, 0.07, 0.09), 'goz', head)
    sphere(f'iris{s}', H + Vector((s * 0.1, -0.265, 0.085)), (0.045, 0.02, 0.045), 'iris', head, subd=0)
    sphere(f'bebek{s}', H + Vector((s * 0.1, -0.28, 0.085)), (0.024, 0.012, 0.024), 'bebek', head, subd=0)
    # Kızgın kaş: içe doğru aşağı eğik
    sphere(f'kas{s}', H + Vector((s * 0.1, -0.235, 0.19)), (0.085, 0.025, 0.022), 'kas', head, rot=(0, -s * 0.5, 0))
    cyl(f'cene{s}', H + Vector((s * 0.06, -0.2, -0.13)), H + Vector((s * 0.03, -0.24, -0.22)), 0.022, 0.006, 'koyu', head)
    curve(f'anten{s}', [H + Vector(p) for p in [(s * 0.07, -0.16, 0.2), (s * 0.12, -0.22, 0.45), (s * 0.3, -0.05, 0.75), (s * 0.55, 0.25, 0.9)]], 0.014, 'koyu', head)
sphere('agiz', H + Vector((0, -0.21, -0.075)), (0.13, 0.05, 0.05), 'agiz', head)
for i in range(-3, 4):  # sıkılmış dişler
    sphere(f'dis{i}', H + Vector((i * 0.03, -0.255, -0.072)), (0.014, 0.008, 0.026), 'dis', head, subd=0)

# ---------- Kollar ve bacaklar ----------
for k, j in J.items():
    s = j['s']
    a, b, c = world(j['sh']), world(j['el']), world(j['wr'])
    sphere(f'omuz_{k}', a, (0.07, 0.07, 0.07), 'kabuk', j['sh'])
    cyl(f'pazu_{k}', a, b, 0.05, 0.04, 'koyu', j['sh'])
    sphere(f'dirsek_{k}', b, (0.045, 0.045, 0.045), 'koyu', j['el'])
    cyl(f'onkol_{k}', b, c, 0.04, 0.032, 'koyu', j['el'])
    for t in (0.35, 0.65):                                                                     # önkol dikenleri
        p = b.lerp(c, t); cyl(f'diken_{k}{t}', p, p + Vector((s * 0.05, 0.03, 0.02)), 0.012, 0.002, 'kas', j['el'], subd=0)
    sphere(f'el_{k}', c + Vector((0, 0, -0.03)), (0.055, 0.05, 0.06), 'koyu', j['wr'])
    for f in (-1, 0, 1):                                                                       # üç pençe
        cyl(f'parmak_{k}{f}', c + Vector((f * 0.03, -0.02, -0.06)), c + Vector((f * 0.045, -0.05, -0.13)), 0.016, 0.004, 'kas', j['wr'], subd=0)
    h, kn, an = world(j['hp']), world(j['kn']), world(j['an'])
    cyl(f'uyluk_{k}', h, kn, 0.075, 0.05, 'kabuk', j['hp'])
    sphere(f'diz_{k}', kn, (0.05, 0.05, 0.05), 'koyu', j['kn'])
    cyl(f'baldir_{k}', kn, an, 0.042, 0.03, 'koyu', j['kn'])
    for t in (0.3, 0.6):
        p = kn.lerp(an, t); cyl(f'bdiken_{k}{t}', p, p + Vector((s * 0.06, 0.02, 0.03)), 0.013, 0.002, 'kas', j['kn'], subd=0)
    sphere(f'ayak_{k}', an + Vector((0, -0.07, -0.0)), (0.06, 0.13, 0.035), 'koyu', j['an'])

# ---------- Kıyafet ----------
# Açık önlü yelek: göğsün dış kabuğu, önden yarık bırakılır.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 1.08))
v = bpy.context.active_object; v.name = 'vest'; v.scale = (0.345, 0.275, 0.385)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
for vert in v.data.vertices:
    z = vert.co.z
    vert.select = (vert.co.y < -0.12 and abs(vert.co.x) < 0.09) or z > 0.3 or z < -0.3   # ön yarık + boyun/etek
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')
sol = v.modifiers.new('kalinlik', 'SOLIDIFY'); sol.thickness = 0.015
finish(v, 'vest', body, 1)
for z in (1.18, 1.05):                                                                         # yelek düğmeleri
    for s in (-1, 1): sphere(f'dugme{z}{s}', (s * 0.1, -0.255, z), (0.018, 0.01, 0.018), 'gold', body, subd=0)
torus('sash', (0, 0, 0.84), 0.31, 0.045, 'sash', body, scale=(1, 0.86, 1))
hat_z = H + Vector((0, -0.02, 0.23))
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.17, radius2=0.14, depth=0.22, location=hat_z + Vector((0, 0, 0.06)))
finish(bpy.context.active_object, 'hat', head, 1).name = 'hat_fes'
sphere('fes_puskul', hat_z + Vector((0, 0.13, 0.05)), (0.02, 0.02, 0.07), 'kas', bpy.data.objects['hat_fes'])
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.24, depth=0.08, location=hat_z + Vector((0, 0.0, 0.0)))
k = finish(bpy.context.active_object, 'hat', head, 1); k.name = 'hat_kasket'
sphere('siper', hat_z + Vector((0, -0.24, -0.02)), (0.16, 0.1, 0.012), 'hat', k)
torus('hat_posu', hat_z + Vector((0, 0, -0.02)), 0.21, 0.075, 'hat', head)
sphere('hat_yemeni', H + Vector((0, 0.02, 0.06)), (0.29, 0.27, 0.25), 'hat', head)
y = bpy.data.objects['hat_yemeni']
for vert in y.data.vertices: vert.select = vert.co.y < -0.08 and vert.co.z < 0.15                # yüz açıklığı
bpy.context.view_layer.objects.active = y
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')

# ---------- Dışa aktar ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True, use_selection=False)
print('YAZILDI', OUT)

if PREVIEW:
    # Önizleme: yemeni hariç fes giydirilmiş tek böcek
    for n in ('hat_kasket', 'hat_posu', 'hat_yemeni'): bpy.data.objects[n].hide_render = True
    for n in ('siper',): bpy.data.objects[n].hide_render = True
    cam = link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam')))
    cam.location = (1.5, -4.2, 1.6); cam.rotation_euler = (math.radians(85), 0, math.radians(20)); cam.data.lens = 50
    scn.camera = cam
    for loc, e in (((3, -3, 4), 900), ((-3, -2, 2), 300), ((0, 3, 3), 500)):
        l = link(bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA'))); l.location = loc; l.data.energy = e; l.data.size = 3
        l.rotation_euler = (Vector((0, 0, 1.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new('w'); scn.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.04, 0.035, 1)
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try: scn.render.engine = eng; break
        except TypeError: pass
    scn.render.resolution_x, scn.render.resolution_y = 700, 900
    scn.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print('ONIZLEME', PREVIEW)
