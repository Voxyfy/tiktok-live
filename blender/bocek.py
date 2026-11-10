# Böcek Düğünü — karikatür hamam böceği modeli v2. Blender'da başsız (headless) çalışır, GLB üretir.
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/bocek.py -- public/models/bocek.glb [önizleme_klasörü]
#
# Eklemler boş nesne (empty) zinciri; dönüşleri sıfır, sahne kodu (dance.js) eksenleri aynen kullanır:
#   body > head, shoulder_R > elbow_R > wrist_R, hip_R > knee_R > ankle_R (L için aynı)
# Konumlar v1 ile aynı tutuldu: omuz 1.28, kol 0.30+0.28, kalça 0.64, bacak 0.32+0.30 (sahne bu ölçülere göre el tutuşturur).
# Yüz -Y yönüne bakar (glTF'te +Z). Kıyafet nesneleri: vest, sash, hat_fes, hat_kasket, hat_posu, hat_yemeni;
# sahne vest/sash/hat malzemelerini böcek başına renklendirir, kullanılmayan başlıkları gizler.
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'bocek.glb'
PREVIEW = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene


def srgb(h):
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def material(name, color, rough=0.5, coat=0.0, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(color), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat:
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.08
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(color), 1); b.inputs['Emission Strength'].default_value = emit
    return m


M = {
    'kabuk':   material('kabuk',   0x5a2610, 0.32, 1.0),     # parlak kitin
    'kanat':   material('kanat',   0x4e1f0a, 0.2, 1.0),      # kanat kabuğu: koyu, cam gibi parlak
    'koyu':    material('koyu',    0x3a1808, 0.4, 0.6),      # uzuvlar
    'krem':    material('krem',    0xd8a464, 0.5, 0.3),      # karın plakaları, kalkan kenarı
    'goz':     material('goz',     0xfbf7ee, 0.12, 0.6),
    'iris':    material('iris',    0xd9902a, 0.25),
    'bebek':   material('bebek',   0x0d0d0d, 0.1),
    'parilti': material('parilti', 0xffffff, 0.0, 0, 0, 3.0),
    'kas':     material('kas',     0x1e0b03, 0.7),
    'agiz':    material('agiz',    0x3a0c0a, 0.6),
    'dis':     material('dis',     0xfdfbf6, 0.2, 0.4),
    'diken':   material('diken',   0x1a0a03, 0.5),
    'vest':    material('vest',    0x222222, 0.75),
    'sash':    material('sash',    0xb5121b, 0.6),
    'hat':     material('hat',     0xb5121b, 0.65),
    'sim':     material('sim',     0xd4a017, 0.28, 0, 0.9),  # yelek kenarı, düğme
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


def finish(o, mat, parent, subd=1, smooth=True):
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


def cyl(name, a, b, r0, r1, mat, parent, subd=1, verts=16):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=r1, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return finish(o, mat, parent, subd)


def torus(name, loc, major, minor, mat, parent, scale=(1, 1, 1), rot=(0, 0, 0), arc=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=40, minor_segments=12, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if arc is not None:  # yay: verilen açı aralığı dışındaki köşeleri sil (kaş, kenar şeridi)
        lo, hi = arc
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
        c = Vector(loc)
        for v in o.data.vertices:
            p = o.matrix_world @ v.co - c
            ang = math.atan2(p.z, p.x) if abs(rot[0]) > 0.1 else math.atan2(p.y, p.x)
            v.select = not (lo <= ang <= hi)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')
    return finish(o, mat, parent, 1)


def curve(name, pts, depth, mat, parent, taper=0.75):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = depth; cu.bevel_resolution = 3
    sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1); sp.use_endpoint_u = True; sp.order_u = 3
    for i, (p, c) in enumerate(zip(sp.points, pts)): p.co = (*c, 1); p.radius = 1 - taper * i / (len(pts) - 1)
    o = link(bpy.data.objects.new(name, cu))
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    return finish(o, mat, parent, 0)


def cut(o, test):
    """Nesneden test(yerel_koordinat) doğru dönen köşeleri sil (yelek ön yarığı, yemeni yüz açıklığı)."""
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
    for v in o.data.vertices: v.select = test(v.co)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')


# ---------- İskelet ----------
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
sphere('gogus', (0, 0.02, 1.04), (0.3, 0.24, 0.36), 'kabuk', body)
# Önde krem karın plakaları: aşağı doğru daralan, üst üste binen boğumlar
for i in range(6):
    z = 0.98 - i * 0.085; w = 0.25 - i * 0.022
    sphere(f'plaka{i}', (0, -0.15 + i * 0.012, z), (w, 0.07, 0.055), 'krem', body, rot=(0.25, 0, 0))
# Sırtta omuz kalkanı (pronotum): koyu orta, krem kenar
sphere('kalkan', (0, 0.135, 1.385), (0.29, 0.23, 0.058), 'kabuk', body, rot=(-0.7, 0, 0))
# Uzun kanat kabukları: arkadan bakınca hamam böceği silueti
for s in (-1, 1):
    # Ortada üst üste binen, sırtın eğimine yatan iki kabuk
    sphere(f'kanat_{s}', (s * 0.075, 0.2, 0.7), (0.19, 0.075, 0.5), 'kanat', body, rot=(-0.18, s * 0.22, s * -0.04), seg=32)

# ---------- Kafa ----------
H = world(head)
sphere('kafa', H + Vector((0, -0.04, 0.05)), (0.3, 0.27, 0.27), 'kabuk', head, seg=32)
sphere('alin', H + Vector((0, -0.16, 0.16)), (0.2, 0.1, 0.08), 'kabuk', head)
for s in (-1, 1):
    e = H + Vector((s * 0.115, -0.22, 0.1))
    sphere(f'goz{s}', e, (0.1, 0.075, 0.105), 'goz', head, seg=32)
    sphere(f'iris{s}', e + Vector((-s * 0.008, -0.07, -0.005)), (0.055, 0.018, 0.058), 'iris', head, subd=0, seg=32)
    sphere(f'bebek{s}', e + Vector((-s * 0.01, -0.084, -0.005)), (0.028, 0.01, 0.032), 'bebek', head, subd=0)
    sphere(f'parilti{s}', e + Vector((-s * 0.03 + 0.02, -0.09, 0.03)), (0.012, 0.006, 0.012), 'parilti', head, subd=0)
    # Kızgın kaş: içe ve aşağı eğik kalın yay
    cyl(f'kas{s}', H + Vector((s * 0.2, -0.24, 0.25)), H + Vector((s * 0.03, -0.29, 0.17)), 0.026, 0.02, 'kas', head)
    lid = sphere(f'kapak{s}', e, (0.106, 0.082, 0.111), 'kabuk', head, seg=32)
    cut(lid, lambda co: co.z < 0.0)            # yalnız üst yarı kalır
    lid.rotation_euler = (0.25, s * 0.42, 0)    # içe ve öne eğ: kızgın bakış
    lid.location = (e - H) + Vector((0, -0.006, -0.012))   # yerel konum: ebeveyn kafa
    # Yanak çıkıntısı ve çene ağzı (mandibula)
    sphere(f'yanak{s}', H + Vector((s * 0.2, -0.16, -0.08)), (0.08, 0.07, 0.07), 'kabuk', head)
    cyl(f'cene{s}', H + Vector((s * 0.08, -0.22, -0.14)), H + Vector((s * 0.03, -0.27, -0.25)), 0.026, 0.006, 'koyu', head)
    # Antenler: alından geriye kıvrılan uzun ince çizgi
    curve(f'anten{s}', [H + Vector(p) for p in [(s * 0.07, -0.2, 0.22), (s * 0.12, -0.27, 0.48), (s * 0.3, -0.12, 0.82), (s * 0.55, 0.2, 1.0), (s * 0.75, 0.55, 0.95)]], 0.013, 'koyu', head, taper=0.85)
sphere('agiz', H + Vector((0, -0.225, -0.08)), (0.15, 0.06, 0.058), 'agiz', head)
for i in range(-4, 5):  # sıkılmış dişler, kenarlara doğru küçülür
    sphere(f'dis{i}', H + Vector((i * 0.03, -0.272, -0.078)), (0.0135, 0.008, 0.03 - abs(i) * 0.002), 'dis', head, subd=0)
cyl('dis_cizgi', H + Vector((-0.13, -0.282, -0.078)), H + Vector((0.13, -0.282, -0.078)), 0.003, 0.003, 'agiz', head, subd=0, verts=6)

# ---------- Kollar ve bacaklar ----------
for k, j in J.items():
    s = j['s']
    a, b, c = world(j['sh']), world(j['el']), world(j['wr'])
    sphere(f'omuz_{k}', a, (0.075, 0.075, 0.075), 'kabuk', j['sh'])
    cyl(f'pazu_{k}', a, b, 0.055, 0.042, 'koyu', j['sh'])
    sphere(f'dirsek_{k}', b, (0.048, 0.048, 0.048), 'kabuk', j['el'])
    cyl(f'onkol_{k}', b, c + Vector((0, 0, 0.03)), 0.045, 0.034, 'koyu', j['el'])
    for t in (0.3, 0.55, 0.8):
        p = b.lerp(c, t); cyl(f'diken_{k}{t}', p, p + Vector((s * 0.05, 0.03, 0.025)), 0.012, 0.001, 'diken', j['el'], subd=0, verts=8)
    sphere(f'avuc_{k}', c + Vector((0, -0.01, -0.03)), (0.06, 0.05, 0.055), 'koyu', j['wr'])
    for f in (-1, 0, 1):  # üç parmak + başparmak, uçları sivri pençe
        base = c + Vector((f * 0.03, -0.025, -0.07))
        cyl(f'parmak_{k}{f}', base, base + Vector((f * 0.012, -0.03, -0.07)), 0.017, 0.011, 'koyu', j['wr'], subd=0, verts=10)
        cyl(f'pence_{k}{f}', base + Vector((f * 0.012, -0.03, -0.07)), base + Vector((f * 0.016, -0.05, -0.1)), 0.011, 0.001, 'diken', j['wr'], subd=0, verts=8)
    cyl(f'basparmak_{k}', c + Vector((-s * 0.045, -0.04, -0.03)), c + Vector((-s * 0.07, -0.08, -0.07)), 0.016, 0.008, 'koyu', j['wr'], subd=0, verts=10)
    h, kn, an = world(j['hp']), world(j['kn']), world(j['an'])
    sphere(f'kalca_{k}', h, (0.08, 0.08, 0.08), 'kabuk', j['hp'])
    cyl(f'uyluk_{k}', h, kn, 0.08, 0.055, 'kabuk', j['hp'])
    sphere(f'diz_{k}', kn, (0.055, 0.055, 0.055), 'koyu', j['kn'])
    cyl(f'baldir_{k}', kn, an + Vector((0, 0, 0.02)), 0.045, 0.032, 'koyu', j['kn'])
    for t in (0.25, 0.5, 0.75):
        p = kn.lerp(an, t); cyl(f'bdiken_{k}{t}', p, p + Vector((s * 0.065, 0.025, 0.035)), 0.014, 0.001, 'diken', j['kn'], subd=0, verts=8)
    sphere(f'topuk_{k}', an + Vector((0, 0.01, 0.01)), (0.045, 0.05, 0.035), 'koyu', j['an'])
    for f in (-1, 0, 1):  # üç parmaklı ayak, öne açılan
        cyl(f'ayak_{k}{f}', an + Vector((f * 0.025, -0.02, -0.005)), an + Vector((f * 0.06, -0.16, -0.02)), 0.022, 0.012, 'koyu', j['an'], subd=0, verts=10)

# ---------- Kıyafet ----------
# Açık önlü yelek: göğsü saran kabuk, ön yarığı ve kol oyukları açık, sim kenarlı
bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, location=(0, 0.05, 1.04))
v = bpy.context.active_object; v.name = 'vest'; v.scale = (0.33, 0.32, 0.385)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
cut(v, lambda co: (co.y < -0.16 and abs(co.x) < 0.075 + (0.3 - co.z) * 0.12) or co.z > 0.29 or co.z < -0.27)
sol = v.modifiers.new('kalinlik', 'SOLIDIFY'); sol.thickness = 0.018; sol.offset = 1
finish(v, 'vest', body, 1)
for s in (-1, 1):  # ön kenarda sim şerit ve düğmeler
    cyl(f'sim_kenar{s}', (s * 0.085, -0.255, 1.3), (s * 0.12, -0.24, 0.8), 0.008, 0.008, 'sim', body, subd=0, verts=8)
    for z in (1.17, 1.06, 0.95):
        sphere(f'dugme{z}{s}', (s * (0.1 + (1.3 - z) * 0.07), -0.262, z), (0.017, 0.01, 0.017), 'sim', body, subd=0)
torus('sim_etek', (0, 0.02, 0.775), 0.315, 0.008, 'sim', body, scale=(1, 0.86, 1))
# Kuşak: belde kalın şal, yanda sarkan iki uç
torus('sash', (0, 0.0, 0.8), 0.3, 0.05, 'sash', body, scale=(1, 0.86, 1))
for i, dx in enumerate((0.0, 0.05)):
    cyl(f'sash_uc{i}', (0.28 + dx, -0.08, 0.8), (0.31 + dx, -0.1, 0.56), 0.035, 0.022, 'sash', body)
for o in [bpy.data.objects[n] for n in ('sash_uc0', 'sash_uc1')]:
    o.parent = bpy.data.objects['sash']; o.matrix_parent_inverse = bpy.data.objects['sash'].matrix_world.inverted()

hat_z = H + Vector((0, -0.02, 0.27))
# Fes: hafif konik, üstte püskül
bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=0.19, radius2=0.155, depth=0.24, location=hat_z + Vector((0, 0, 0.06)))
fes = finish(bpy.context.active_object, 'hat', head, 0); fes.name = 'hat_fes'
bev = fes.modifiers.new('pah', 'BEVEL'); bev.width = 0.015; bev.segments = 3; bev.limit_method = 'ANGLE'
cyl('fes_ip', hat_z + Vector((0, 0, 0.18)), hat_z + Vector((0, 0.13, 0.1)), 0.006, 0.006, 'kas', fes, subd=0, verts=6)
sphere('fes_puskul', hat_z + Vector((0, 0.15, 0.02)), (0.025, 0.025, 0.08), 'kas', fes)
# Kasket: yumuşak tepe, siper
sphere('hat_kasket', hat_z + Vector((0, 0.02, 0.0)), (0.27, 0.27, 0.1), 'hat', head)
sphere('siper', hat_z + Vector((0, -0.25, -0.04)), (0.18, 0.11, 0.014), 'hat', bpy.data.objects['hat_kasket'])
# Poşu: başa sarılı şal + yanda düğüm
torus('hat_posu', hat_z + Vector((0, 0, -0.03)), 0.23, 0.08, 'hat', head, scale=(1, 1, 0.9))
sphere('posu_dugum', hat_z + Vector((0.22, 0.05, -0.04)), (0.06, 0.05, 0.06), 'hat', bpy.data.objects['hat_posu'])
# Yemeni: başı saran örtü, yüz açık, kenarında oya
y = sphere('hat_yemeni', H + Vector((0, 0.02, 0.07)), (0.32, 0.3, 0.29), 'hat', head, seg=32)
cut(y, lambda co: co.y < -0.06 and co.z < 0.16)
for i in range(14):
    a = -math.pi * 0.95 + i / 13 * math.pi * 0.9
    sphere(f'oya{i}', H + Vector((math.cos(a) * 0.3, -0.06 + math.sin(a) * 0.05, 0.16)), (0.02, 0.02, 0.02), 'sim', y, subd=0)

# ---------- Dışa aktar ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True, use_selection=False)
print('YAZILDI', OUT)

if PREVIEW:
    import os
    for n in ('hat_kasket', 'hat_posu', 'hat_yemeni'):
        for o in [bpy.data.objects[n]] + list(bpy.data.objects[n].children_recursive): o.hide_render = True
    M['vest'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*srgb(0x1d3557), 1)
    w = bpy.data.worlds.new('w'); scn.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*srgb(0x2a2440), 1); bg.inputs['Strength'].default_value = 0.6
    for loc, e, c in (((3, -3, 4), 900, (1, .9, .8)), ((-3, -2, 2), 250, (.7, .8, 1)), ((0, 4, 3), 700, (1, .7, .5))):
        l = link(bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA'))); l.location = loc; l.data.energy = e; l.data.size = 2.5; l.data.color = c
        l.rotation_euler = (Vector((0, 0, 1.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scn.render.engine = 'BLENDER_EEVEE'
    scn.render.resolution_x, scn.render.resolution_y = 640, 900
    cam = link(bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))); cam.data.lens = 50; scn.camera = cam
    for nm, loc in (('on', (1.2, -4.4, 1.5)), ('arka', (-1.4, 4.2, 1.7))):
        cam.location = loc; cam.rotation_euler = (Vector((0, 0, 1.15)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scn.render.filepath = os.path.join(PREVIEW, f'bocek_{nm}.png'); bpy.ops.render.render(write_still=True)
    print('ONIZLEME', PREVIEW)
