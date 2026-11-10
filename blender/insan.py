# Higgsfield/Meshy'den gelen iskeletli insan modelini sahneye hazırlar:
#   Blender -b -P blender/insan.py -- <ham.glb> <çıktı.glb> [doku_boyutu=1024]
# - Meshy'nin yardımcı küresini ve hazır animasyon kliplerini siler (dansı sahne kodu yapar)
# - Dokuyu telefon için küçültür
# - İskelet ve deri ağırlıkları olduğu gibi kalır; kemik adları Mixamo düzeninde (Hips, LeftArm, LeftForeArm, ...)
import bpy, sys

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
TEX = int(argv[2]) if len(argv) > 2 else 1024

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

for o in list(bpy.data.objects):
    if o.type == 'MESH' and not o.parent and not any(m.type == 'ARMATURE' for m in o.modifiers):
        bpy.data.objects.remove(o)            # Meshy'nin iskelete bağlı olmayan yardımcı küresi
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    if arm.animation_data: arm.animation_data_clear()
    for pb in arm.pose.bones:                  # dinlenme duruşuna dön
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
for img in bpy.data.images:
    if img.size[0] > TEX:
        img.scale(TEX, TEX)
        img.pack()

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_animations=False, export_image_format='JPEG', export_jpeg_quality=88)
print('YAZILDI', OUT)
