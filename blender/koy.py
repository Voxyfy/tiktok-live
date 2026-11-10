# Böcek Düğünü — köy meydanı ve orkestra çalgıları. Blender'da başsız çalışır:
#   Blender -b -P blender/koy.py -- public/models/koy.glb public/models/calgi.glb [önizleme.png]
#
# Konumlar sahnedeki (three.js) koordinatlarla verilir: x sağ, y yukarı, z kameraya doğru.
# Blender'a çevirme T(x, y, z) = (x, -z, y). Meydan merkezi = halay merkezi (0, 0, -1.4).
# Her yapı kendi yerel düzleminde (ön yüz -Y) kurulur, sonra bir boş nesneyle yerine taşınır.
# Sahne kodu düğümleri adıyla bulur: "masa", "orkestra_sahne", "koltuk_gelin", "koltuk_damat".
# calgi.glb: davul, tokmak, cubuk, zurna — kökleri tutma noktasında, böceğin eline takılır.
import bpy, sys, math, random, os
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT, OUT_PROPS = argv[0], argv[1]
PREVIEW = argv[2] if len(argv) > 2 else None
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tex')
os.makedirs(TEX, exist_ok=True)
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene


def T(x, y, z): return Vector((x, -z, y))


def srgb(h):
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def material(name, color, rough=0.7, metal=0.0, coat=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(color), 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*srgb(color), 1); b.inputs['Emission Strength'].default_value = emit
    return m


M = {k: material(k, *v) for k, v in {
    'badana': (0xefe8dc, 0.92), 'badana2': (0xe6dccb, 0.92), 'tas': (0x9a8f80, 0.95), 'tas_koyu': (0x6f665a, 0.95),
    'ahsap': (0x4f321d, 0.75), 'ahsap_acik': (0x8a5a34, 0.7), 'cumba': (0x6e4426, 0.7),
    'kiremit': (0xb4532a, 0.75), 'kiremit2': (0x8f3d1e, 0.85),
    'cam': (0xffc66b, 0.3, 0, 0, 2.5), 'kepenk': (0x2f5d50, 0.7), 'kepenk2': (0x6a2e2a, 0.7),
    'yaprak': (0x2c6327, 0.85), 'yaprak2': (0x3d7d32, 0.85), 'yaprak3': (0x4f8f3a, 0.85), 'govde': (0x5a4434, 0.95),
    'su': (0x2f6f96, 0.04, 0, 1.0), 'ortu': (0xfbf8f2, 0.85), 'sim': (0xd4a017, 0.3, 0.9),
    'kadife': (0x8e1620, 0.55), 'cicek_k': (0xe63950, 0.6), 'cicek_b': (0xfffaf0, 0.6), 'cicek_p': (0xffafcc, 0.6),
    'yesil': (0x34602a, 0.9), 'ampul_s': (0xffd98a, 0.3, 0, 0, 8), 'ampul_k': (0xff6b6b, 0.3, 0, 0, 8),
    'ampul_m': (0x7bdff2, 0.3, 0, 0, 8), 'ampul_y': (0xb8f28a, 0.3, 0, 0, 8), 'kablo': (0x141414, 0.6),
    'bayrak_k': (0xd62828, 0.7), 'bayrak_b': (0xf6f1e9, 0.7), 'dag': (0x231d31, 1.0), 'dag2': (0x2f2640, 1.0),
    'kilim1': (0xa4161a, 0.95), 'kilim2': (0xe9c46a, 0.95), 'kilim3': (0x264653, 0.95), 'kilim4': (0xf4f1de, 0.95),
    'metal': (0xc9b27c, 0.25, 1.0), 'deri': (0xeadfc4, 0.55), 'davul': (0x9b1d20, 0.45, 0, 0.5), 'ip': (0xd9c9a3, 0.8),
    'zurna': (0xc4874a, 0.35, 0, 0.7),   # açık ceviz: koyu kabuk üstünde seçilsin
}.items()}

coll_koy = bpy.data.collections.new('koy'); scn.collection.children.link(coll_koy)
coll_props = bpy.data.collections.new('calgi'); scn.collection.children.link(coll_props)
CUR = [coll_koy]


def put(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    CUR[0].objects.link(o); return o


def finish(o, mat, parent=None, smooth=False, bevel=0.0, subd=0):
    o.data.materials.clear(); o.data.materials.append(M[mat] if isinstance(mat, str) else mat)
    for p in o.data.polygons: p.use_smooth = smooth
    if bevel:
        b = o.modifiers.new('pah', 'BEVEL'); b.width = bevel; b.segments = 2; b.limit_method = 'ANGLE'
    if subd:
        s = o.modifiers.new('sub', 'SUBSURF'); s.levels = subd; s.render_levels = subd
    if parent: o.parent = parent          # ebeveyn özdeşlik dönüşümündeyken kurulur: yerel = dünya
    return put(o)


def box(name, c, size, mat, parent=None, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    return finish(o, mat, parent, bevel=bevel)


def cyl(name, c, r, h, mat, parent=None, verts=24, rot=(0, 0, 0), r2=None, smooth=True, bevel=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=h, location=c, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return finish(o, mat, parent, smooth=smooth, bevel=bevel)


def seg(name, a, b, r0, r1, mat, parent=None, verts=12):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=r1, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return finish(o, mat, parent, smooth=True)


def ball(name, c, r, mat, parent=None, scale=(1, 1, 1), sub=2, smooth=True):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=c)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    return finish(o, mat, parent, smooth=smooth)


def group(name):
    e = bpy.data.objects.new(name, None); return put(e)


def place(g, x, z, ry=0.0, y=0.0):
    """Yerel düzlemde kurulmuş grubu sahne konumuna taşı (ry: y ekseni etrafında, radyan)."""
    g.location = T(x, y, z); g.rotation_euler = (0, 0, ry)


# ---------- Pişirilmiş doku: arnavut kaldırımı (Cycles ile prosedürelden resme) ----------
def bake_cobble(obj):
    img = bpy.data.images.new('arnavut', 2048, 2048)
    img.filepath_raw = os.path.join(TEX, 'arnavut.png'); img.file_format = 'PNG'
    m = bpy.data.materials.new('arnavut'); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 70
    vor2 = nt.nodes.new('ShaderNodeTexVoronoi'); vor2.inputs['Scale'].default_value = 70
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 60
    for n in (vor, vor2, noise): nt.links.new(tc.outputs['UV'], n.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = 0.0; r.elements[0].color = (*srgb(0x231e19), 1)
    r.elements[1].position = 0.09; r.elements[1].color = (*srgb(0xb3a48e), 1)
    nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac'])
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs['Factor'].default_value = 0.35
    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(vor2.outputs['Color'], bw.inputs['Color'])
    nt.links.new(ramp.outputs['Color'], m1.inputs['A']); nt.links.new(bw.outputs['Val'], m1.inputs['B'])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'OVERLAY'; m2.inputs['Factor'].default_value = 0.25
    nt.links.new(m1.outputs['Result'], m2.inputs['A']); nt.links.new(noise.outputs['Color'], m2.inputs['B'])
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; nt.nodes.active = tex
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(m2.outputs['Result'], em.inputs['Color']); nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    obj.data.materials.clear(); obj.data.materials.append(m)
    scn.render.engine = 'CYCLES'; scn.cycles.samples = 2; scn.cycles.device = 'CPU'
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type='EMIT', margin=2)
    img.save()
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color']); nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    b.inputs['Roughness'].default_value = 0.85


# ---------- Zemin ----------
bpy.ops.mesh.primitive_circle_add(vertices=96, radius=8.2, fill_type='NGON', location=T(0, 0.005, -1.4))
plaza = bpy.context.active_object; plaza.name = 'meydan'; put(plaza)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.cube_project(cube_size=16.4); bpy.ops.object.mode_set(mode='OBJECT')
bake_cobble(plaza)
bpy.ops.mesh.primitive_circle_add(vertices=64, radius=70, fill_type='NGON', location=T(0, -0.01, -1.4))
finish(bpy.context.active_object, 'yesil').name = 'cimen'
for i in range(80):  # meydan kenarında taş bordür
    a = i / 80 * math.tau
    box(f'bordur{i}', T(math.sin(a) * 8.3, 0.07, -1.4 + math.cos(a) * 8.3), (0.6, 0.18, 0.16), 'tas_koyu', rot=(0, 0, a), bevel=0.04)


# ---------- Ev: taş temel, badanalı alt kat, öne taşan ahşap kirişli üst kat (cumba), kiremit çatı ----------
def house(name, x, z, ry, w=3.4, d=3.0, h1=2.2, h2=1.9, kepenk='kepenk', badana='badana'):
    g = group(name)
    F = -d / 2  # ön yüz (-Y)
    box('taban', (0, 0, 0.35), (w + 0.1, d + 0.1, 0.7), 'tas', g, bevel=0.04)
    box('alt_kat', (0, 0, 0.7 + (h1 - 0.7) / 2), (w, d, h1 - 0.7), badana, g, bevel=0.03)
    box('ust_kat', (0, -0.15, h1 + h2 / 2), (w + 0.2, d + 0.3, h2), badana, g, bevel=0.03)
    F2 = F - 0.3
    for sx in (-1, 1):
        box('dikme', (sx * (w / 2 + 0.1), F2 - 0.01, h1 + h2 / 2), (0.13, 0.13, h2), 'ahsap', g)
    box('kat_kirisi', (0, F2 - 0.02, h1), (w + 0.4, 0.16, 0.16), 'ahsap', g)
    box('sacak_kirisi', (0, F2 - 0.02, h1 + h2), (w + 0.4, 0.16, 0.14), 'ahsap', g)
    for i in range(-2, 3):
        box('payanda', (i * (w / 4.6), F + 0.0, h1 - 0.22), (0.08, 0.42, 0.08), 'ahsap', g, rot=(-0.75, 0, 0))
    box('orta_kiris', (0, F2 - 0.015, h1 + h2 * 0.5 - 0.5), (w + 0.2, 0.1, 0.1), 'ahsap', g)
    # Pencereler: çerçeve, sıcak ışıklı cam, kayıt, iki kanat kepenk
    def window(px, pz, fy, fh=0.8):
        box('pen_cerceve', (px, fy - 0.02, pz), (0.68, 0.06, fh + 0.12), 'ahsap', g)
        box('pen_cam', (px, fy - 0.045, pz), (0.54, 0.03, fh), 'cam', g)
        box('pen_kayit', (px, fy - 0.07, pz), (0.04, 0.02, fh), 'ahsap', g)
        box('pen_kayit2', (px, fy - 0.07, pz + fh * 0.15), (0.54, 0.02, 0.04), 'ahsap', g)
        for sx in (-1, 1):
            box('kepenk', (px + sx * 0.47, fy - 0.03, pz), (0.26, 0.04, fh + 0.06), kepenk, g)
    window(-w * 0.27, h1 + h2 * 0.52, F2)
    window(w * 0.27, h1 + h2 * 0.52, F2)
    window(w * 0.27, 1.45, F, 0.65)
    box('kapi', (-w * 0.27, F - 0.03, 0.75 + 0.65), (0.82, 0.08, 1.3), 'ahsap_acik', g, bevel=0.02)
    for k in range(3): box('kapi_tahta', (-w * 0.27 - 0.27 + k * 0.27, F - 0.075, 1.4), (0.02, 0.01, 1.25), 'ahsap', g)
    box('kapi_kemer', (-w * 0.27, F - 0.04, 2.1), (1.0, 0.12, 0.14), 'tas_koyu', g)
    box('basamak', (-w * 0.27, F - 0.3, 0.08), (1.0, 0.5, 0.16), 'tas', g, bevel=0.03)
    # Beşik çatı + tek tek kiremit sıraları
    rw, rd, rh = w + 0.8, d + 1.0, 1.15
    top = h1 + h2 + 0.07; cy = -0.15
    slope = math.atan2(rh, rd / 2); L = math.hypot(rh, rd / 2)
    for side, a in ((-1, slope), (1, -slope)):
        c = Vector((0, cy + side * rd / 4, top + rh / 2))
        box('cati', c, (rw, L, 0.08), 'kiremit2', g, rot=(a, 0, 0))
        normal = Vector((0, -math.sin(a), math.cos(a)))
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.085, depth=L * 1.03, location=c + normal * 0.06 + Vector((-rw / 2 + 0.09, 0, 0)), rotation=(math.pi / 2 + a, 0, 0))
        t = bpy.context.active_object; t.name = 'kiremit'
        arr = t.modifiers.new('dizi', 'ARRAY'); arr.use_relative_offset = False; arr.use_constant_offset = True
        arr.constant_offset_displace = (0.17, 0, 0); arr.count = int((rw - 0.1) / 0.17)
        finish(t, 'kiremit', g, smooth=True)
    box('mahya', (0, cy, top + rh + 0.03), (rw + 0.05, 0.2, 0.18), 'kiremit', g)
    box('baca', (w * 0.3, cy + 0.5, top + rh + 0.1), (0.42, 0.42, 1.1), 'tas', g, bevel=0.03)
    box('baca_sapka', (w * 0.3, cy + 0.5, top + rh + 0.7), (0.58, 0.58, 0.08), 'tas_koyu', g)
    place(g, x, z, ry)
    return g


house('ev1', -6.4, -10.6, 0.3, kepenk='kepenk')
house('ev2', -2.2, -12.6, 0.05, w=3.8, kepenk='kepenk2', badana='badana2')
house('ev3', 2.4, -12.2, -0.08, kepenk='kepenk')
house('ev4', 6.6, -10.2, -0.35, w=3.2, kepenk='kepenk2')
house('ev5', -10.2, -5.4, 0.95, w=3.2, h2=1.7, badana='badana2')
house('ev6', 10.2, -5.0, -0.95, w=3.2, h2=1.7, kepenk='kepenk2')
house('ev7', -5.0, -17.0, 0.1, w=3.0, h1=2.0, h2=1.6)
house('ev8', 5.4, -17.4, -0.15, w=3.0, h1=2.0, h2=1.6, badana='badana2')


# ---------- Çınar: dallı gövde, kümeli yaprak taçları ----------
def cinar(name, x, z, s=1.0):
    g = group(name)
    seg('govde', (0, 0, 0), (0.1, 0.1, 2.6 * s), 0.42 * s, 0.26 * s, 'govde', g, verts=14)
    tips = []
    for i in range(6):
        a = i / 6 * math.tau + 0.3
        base = Vector((0.08, 0.08, (2.1 + 0.15 * (i % 3)) * s))
        tip = base + Vector((math.cos(a) * 1.5 * s, math.sin(a) * 1.3 * s, (1.1 + random.random() * 0.7) * s))
        seg('dal', base, tip, 0.17 * s, 0.07 * s, 'govde', g, verts=10); tips.append(tip)
    for i, tip in enumerate(tips + [Vector((0, 0, 4.6 * s))]):
        for k in range(3):
            off = Vector(((random.random() - .5) * 1.0 * s, (random.random() - .5) * 1.0 * s, (random.random() - .2) * 0.7 * s))
            ball('yaprak', tip + off, (0.95 + random.random() * 0.45) * s, ['yaprak', 'yaprak2', 'yaprak3'][(i + k) % 3], g, sub=2, smooth=False)
    place(g, x, z)


cinar('cinar1', -6.3, -6.6, 1.15)
cinar('cinar2', 7.6, -8.6, 0.95)
cinar('cinar3', -12.5, -12.0, 1.1)
cinar('cinar4', 12.5, -13.0, 1.2)

# ---------- Taş çeşme: kemerli ayna taşı, oluk, sekizgen yalak, su ----------
g = group('cesme')
box('cesme_ayna', (0, 0.3, 1.2), (1.6, 0.4, 2.4), 'tas', g, bevel=0.05)
box('cesme_kemer', (0, 0.07, 1.6), (1.0, 0.1, 1.1), 'tas_koyu', g, bevel=0.03)
box('cesme_tepe', (0, 0.3, 2.48), (1.85, 0.55, 0.18), 'tas_koyu', g, bevel=0.03)
seg('cesme_oluk', (0, 0.05, 1.2), (0, -0.3, 1.12), 0.04, 0.035, 'metal', g)
cyl('cesme_yalak', (0, -0.55, 0.32), 0.85, 0.64, 'tas', g, verts=8, smooth=False, bevel=0.03)
cyl('cesme_su', (0, -0.55, 0.6), 0.74, 0.04, 'su', g, verts=8, smooth=False)
place(g, 5.6, -7.2, -0.5)

# ---------- Düğün masası, gelin-damat koltukları, çiçekli kemer ----------
TABLE_Z, TABLE_X = -5.2, 0.6   # masa biraz sağda: dikey çerçevede solda orkestraya yer kalsın
g = group('masa')
box('masa_ust', (0, 0, 0.78), (3.6, 1.2, 0.06), 'ahsap', g)
box('masa_ortu', (0, 0, 0.42), (3.7, 1.3, 0.74), 'ortu', g, bevel=0.06)
box('masa_yolluk', (0, 0, 0.815), (3.75, 0.4, 0.01), 'sim', g)
for i, px in enumerate((-1.2, -0.4, 0.4, 1.2)):
    ball('masa_cicek', (px, 0, 0.92), 0.12, ['cicek_k', 'cicek_b', 'cicek_p', 'cicek_k'][i], g, scale=(1, 1, .8))
    cyl('masa_mum', (px + 0.2, 0.1, 0.9), 0.025, 0.18, 'cicek_b', g, verts=8)
place(g, TABLE_X, TABLE_Z)
for nm, px in (('koltuk_gelin', -0.6), ('koltuk_damat', 0.6)):
    g = group(nm)
    box('koltuk_oturak', (0, 0, 0.5), (0.7, 0.6, 0.12), 'kadife', g, bevel=0.03)
    box('koltuk_sirt', (0, 0.28, 1.15), (0.72, 0.1, 1.3), 'kadife', g, bevel=0.05)
    box('koltuk_cerceve', (0, 0.33, 1.15), (0.82, 0.06, 1.42), 'sim', g, bevel=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1): seg('koltuk_ayak', (sx * 0.3, sy * 0.25, 0), (sx * 0.3, sy * 0.25, 0.45), 0.03, 0.03, 'sim', g, verts=8)
    place(g, TABLE_X + px, TABLE_Z - 0.85)
g = group('kemer')
for sx in (-1, 1): cyl('kemer_direk', (sx * 2.2, 0, 1.4), 0.06, 2.8, 'cicek_b', g, verts=12)
bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.06, major_segments=48, minor_segments=8, location=(0, 0, 2.8), rotation=(math.pi / 2, 0, 0))
t = bpy.context.active_object; t.name = 'kemer_yay'
import bmesh
bm = bmesh.new(); bm.from_mesh(t.data)   # alt yarıyı sil: yalnız üst yay kalsın (döndürülmüş torusta yerel +Y yukarı)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.02], context='VERTS'); bm.to_mesh(t.data); bm.free()
finish(t, 'cicek_b', g, smooth=True)
for i in range(46):
    a = i / 45 * math.pi
    p = Vector((math.cos(a) * 2.2, 0, 2.8 + math.sin(a) * 2.2))
    if i % 4 == 0: ball('kemer_yaprak', p + Vector((0, 0.08, -0.08)), 0.16, 'yaprak2', g, scale=(1.4, .5, .8), sub=1, smooth=False)
    ball('kemer_cicek', p + Vector(((random.random() - .5) * .1, -0.05, (random.random() - .5) * .1)), 0.11 + random.random() * 0.05, ['cicek_k', 'cicek_b', 'cicek_p'][i % 3], g, sub=1)
for sx in (-1, 1):
    for k in range(8):
        ball('kemer_cicek', (sx * 2.2 + (random.random() - .5) * .1, -0.05, 0.4 + k * 0.32), 0.1, ['cicek_k', 'cicek_b', 'cicek_p'][k % 3], g, sub=1)
place(g, TABLE_X, TABLE_Z - 1.4)

# ---------- Orkestra sahnesi: tahta platform, kilim, arkada bez ----------
STAGE = (-2.75, -5.65)
g = group('orkestra_sahne')
box('sahne_platform', (0, 0, 0.18), (2.8, 1.9, 0.36), 'ahsap_acik', g, bevel=0.03)
for k in range(9): box('sahne_tahta', (-1.4 + 0.31 * k + 0.155, -0.951, 0.18), (0.02, 0.01, 0.34), 'ahsap', g)
box('kilim', (0, 0.05, 0.365), (2.2, 1.4, 0.01), 'kilim1', g)
box('kilim_ic', (0, 0.05, 0.368), (1.8, 1.0, 0.01), 'kilim3', g)
box('kilim_orta', (0, 0.05, 0.371), (1.3, 0.55, 0.01), 'kilim2', g)
for i in range(5): box('kilim_motif', (-0.5 + i * 0.25, 0.05, 0.374), (0.14, 0.14, 0.01), 'kilim4', g, rot=(0, 0, math.pi / 4))
for sx in (-1, 1): seg('sahne_direk', (sx * 1.35, 0.9, 0.36), (sx * 1.35, 0.9, 2.9), 0.05, 0.05, 'ahsap', g, verts=8)
box('sahne_bez', (0, 0.92, 2.2), (2.6, 0.03, 1.2), 'kilim1', g)
box('sahne_bez_serit', (0, 0.9, 2.2), (2.6, 0.03, 0.3), 'kilim2', g)
place(g, STAGE[0], STAGE[1], 0.45); g.scale = (0.82, 0.82, 0.82)


# ---------- Ampul zinciri ve bayrak süsü (sarkık eğriler) ----------
def garland(name, a, b, sag, n, flags):
    g = group(name)
    pts = []
    for i in range(n + 1):
        t = i / n; p = a.lerp(b, t); p.z -= math.sin(math.pi * t) * sag; pts.append(p)
    for i in range(n): seg('kablo', pts[i], pts[i + 1], 0.012, 0.012, 'kablo', g, verts=6)
    for i, p in enumerate(pts[1:-1], 1):
        if flags:
            bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.2, depth=0.01, location=p + Vector((0, 0, -0.2)), rotation=(math.pi / 2, 0, random.random() * 0.3))
            o = bpy.context.active_object; o.name = 'bayrak'; o.scale = (1, 1.4, 1)
            finish(o, 'bayrak_k' if i % 2 else 'bayrak_b', g)
        else:
            ball('ampul', p + Vector((0, 0, -0.07)), 0.065, ['ampul_s', 'ampul_k', 'ampul_m', 'ampul_y', 'ampul_s'][i % 5], g, sub=1)


poles = [T(-6.0, 4.6, -6.4), T(6.0, 4.6, -6.4), T(-6.6, 4.6, 2.6), T(6.6, 4.6, 2.6)]
for i, p in enumerate(poles):
    seg(f'direk{i}', p - Vector((0, 0, 4.6)), p + Vector((0, 0, 0.1)), 0.09, 0.07, 'ahsap', verts=10)
garland('ampul_arka', poles[0], poles[1], 0.9, 30, False)
garland('bayrak_arka', poles[0] + Vector((0, 0, -0.3)), poles[1] + Vector((0, 0, -0.3)), 1.3, 22, True)
garland('ampul_sol', poles[0], poles[2], 0.8, 26, False)
garland('ampul_sag', poles[1], poles[3], 0.8, 26, False)
garland('ampul_capraz1', poles[0], poles[3], 1.6, 36, False)
garland('ampul_capraz2', poles[1], poles[2], 1.6, 36, False)

# ---------- Uzak dağlar ----------
for i in range(11):
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=10 + random.random() * 8, depth=10 + random.random() * 12, location=T(-60 + i * 12, 4, -58 - random.random() * 10))
    finish(bpy.context.active_object, 'dag' if i % 2 else 'dag2').name = 'dag'

# ---------- Çalgılar (ayrı dosya) ----------
CUR[0] = coll_props
# Davul: kökü göğüste taşıma noktası, eksen yanlara (x)
g = group('davul')
cyl('davul_govde', (0, 0, 0), 0.4, 0.42, 'davul', g, verts=36, rot=(0, math.pi / 2, 0))
for sx in (-1, 1):
    cyl('davul_deri', (sx * 0.215, 0, 0), 0.41, 0.012, 'deri', g, verts=36, rot=(0, math.pi / 2, 0))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.41, minor_radius=0.022, major_segments=36, minor_segments=8, location=(sx * 0.215, 0, 0), rotation=(0, math.pi / 2, 0))
    finish(bpy.context.active_object, 'ahsap', g, smooth=True).name = 'davul_cember'
for i in range(14):  # zikzak gergi ipi
    a1 = i / 14 * math.tau; a2 = (i + 0.5) / 14 * math.tau
    seg('davul_ip', (-0.2, math.cos(a1) * 0.4, math.sin(a1) * 0.4), (0.2, math.cos(a2) * 0.4, math.sin(a2) * 0.4), 0.007, 0.007, 'ip', g, verts=5)
g = group('tokmak')  # kökü tutma noktası, sap -Z yönünde aşağı değil: elden ileri (-Y)
seg('tokmak_sap', (0, 0, 0), (0, -0.42, 0.05), 0.016, 0.014, 'ahsap', g, verts=8)
ball('tokmak_bas', (0, -0.45, 0.06), 0.06, 'deri', g, scale=(1, 1, 0.9))
g = group('cubuk')
seg('cubuk_sap', (0, 0, 0), (0, -0.48, 0.02), 0.008, 0.006, 'ahsap', g, verts=6)
g = group('zurna')  # kökü ağızlık; gövde -Y (ileri) ve biraz aşağı
seg('zurna_agizlik', (0, 0, 0), (0, -0.06, -0.01), 0.008, 0.012, 'metal', g, verts=8)
seg('zurna_govde', (0, -0.06, -0.01), (0, -0.5, -0.12), 0.022, 0.04, 'zurna', g, verts=16)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.04, radius2=0.11, depth=0.14, location=(0, -0.56, -0.135))
o = bpy.context.active_object; o.name = 'zurna_kalak'
o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector((0, -0.5, -0.12)).normalized())
finish(o, 'zurna', g, smooth=True)
for k in range(7): ball('zurna_delik', (0, -0.16 - k * 0.045, -0.035 - k * 0.011 + 0.022), 0.008, 'kablo', g, sub=1)
bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.006, location=(0, -0.08, -0.015), rotation=(math.pi / 2 - 0.24, 0, 0))
finish(bpy.context.active_object, 'metal', g, smooth=True).name = 'zurna_bilezik'


# Karadeniz kemençesi: dar armut gövde, kısa sap, üç burgu, üç tel. Kökü gövdenin alt ucu (dik tutulur, +Z yukarı)
g = group('kemence')
gov = ball('kemence_govde', (0, 0, 0.22), 0.1, 'zurna', g, scale=(0.62, 0.42, 2.3), sub=3)
box('kemence_kapak', (0, -0.04, 0.22), (0.1, 0.006, 0.36), 'ahsap_acik', g)
cyl('kemence_sap', (0, 0, 0.5), 0.028, 0.14, 'ahsap', g, verts=12)
box('kemence_bas', (0, 0, 0.6), (0.06, 0.035, 0.07), 'ahsap', g, bevel=0.01)
for k in (-1, 0, 1):
    seg('kemence_burgu', (k * 0.022, 0.0, 0.6), (k * 0.022, 0.06, 0.6), 0.007, 0.01, 'kablo', g, verts=6)
    seg('kemence_tel', (k * 0.012, -0.05, 0.08), (k * 0.012, -0.03, 0.58), 0.0015, 0.0015, 'metal', g, verts=4)
box('kemence_esik', (0, -0.05, 0.16), (0.05, 0.01, 0.012), 'cicek_b', g)
# Kemençe yayı: kökü tutma yeri, yay yana (-X) uzanır
g = group('kemence_yay')
seg('yay_cubuk', (0, 0, 0), (-0.55, 0, 0.03), 0.006, 0.004, 'ahsap', g, verts=6)
seg('yay_kil', (-0.03, 0, -0.02), (-0.53, 0, 0.0), 0.003, 0.003, 'deri', g, verts=4)

# ---------- Dışa aktar ----------
def export(coll, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.all_objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True, use_selection=True, export_image_format='JPEG', export_jpeg_quality=85)
    print('YAZILDI', path)


export(coll_koy, OUT)
export(coll_props, OUT_PROPS)

if PREVIEW:
    for o in coll_props.all_objects: o.hide_render = True
    w = bpy.data.worlds.new('w'); scn.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (*srgb(0x241d38), 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
    sun = bpy.data.objects.new('ay', bpy.data.lights.new('ay', 'SUN')); scn.collection.objects.link(sun)
    sun.data.energy = 1.2; sun.data.color = (0.75, 0.8, 1.0); sun.rotation_euler = (0.9, 0.2, -0.6)
    for p in ((-3, -3), (3, -3), (0, 1.5)):
        l = bpy.data.objects.new('isik', bpy.data.lights.new('isik', 'POINT')); scn.collection.objects.link(l)
        l.location = T(p[0], 3.6, p[1]); l.data.energy = 900; l.data.color = (1, 0.72, 0.42)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.lens = 24; cam.location = T(0, 6.5, 12.5)
    cam.rotation_euler = (T(0, 1.2, -4.0) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scn.render.engine = 'BLENDER_EEVEE'; scn.render.resolution_x, scn.render.resolution_y = 720, 1280
    scn.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)
    print('ONIZLEME', PREVIEW)
