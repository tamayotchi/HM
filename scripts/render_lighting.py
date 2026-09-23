"""Render saved, independent floor models; never overwrite their .blend files.
FP_FLOOR=3 (or 1,3) selects rendered floors; all marker projections are refreshed.
FP_PROJECT_ONLY=1 refreshes projections without rendering.
FP_RENDER_DIR and FP_RENDER_STATES=base,all-on are useful for read-only smoke tests.
FP_MODEL_1 (or _2/_3/_4) temporarily renders a staged model without changing config paths.
"""
import bpy
import json
import math
import os
import sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import ROOT, RENDERS, PROJECTED, ensure_output_dirs, load_config

ensure_output_dirs()
config = load_config()
raw = Path(os.environ.get('FP_RENDER_DIR', str(RENDERS)))
raw.mkdir(parents=True, exist_ok=True)
selected = set(os.environ.get('FP_FLOOR', ','.join(str(f['floor']) for f in config['floors'])).split(','))
assert selected <= {str(f['floor']) for f in config['floors']}, 'Unknown floor selection'
states = set(os.environ['FP_RENDER_STATES'].split(',')) if os.getenv('FP_RENDER_STATES') else None

for floor in config['floors']:
    number = floor['floor']
    model_path = Path(os.environ.get(f'FP_MODEL_{number}', str(ROOT / floor['model_file'])))
    bpy.ops.wm.open_mainfile(filepath=str(model_path))
    assert len(bpy.data.scenes) == 1, 'Each editable model must contain exactly one floor scene'
    scene = bpy.data.scenes[floor['scene']]
    bpy.context.window.scene = scene
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'OPTIX'
        gpu = any(device.use for device in prefs.devices)
    except (TypeError, RuntimeError):
        gpu = False
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU' if gpu else 'CPU'
    scene.cycles.samples = 160
    scene.cycles.seed = 42
    scene.cycles.use_animated_seed = False
    scene.cycles.adaptive_threshold = .008
    scene.render.resolution_x = scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 65
    scene.render.image_settings.color_depth = '8'

    # Saved files already include their camera, ambient lighting and packed textures.
    # Circuit lamps are managed by JSON, so remove them before recreating them.
    for obj in list(scene.objects):
        if obj.type == 'LIGHT' and (obj.get('floorplan_generated') or obj.name.startswith('Circuit · ')):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.lights.remove(data)
    origin = Vector(floor.get('coordinate_origin', (23, -22.85, 0)))
    scale = Vector(floor.get('coordinate_scale', (1, 1, 1)))

    def local(point):
        delta = Vector(point) - origin
        return Vector((delta.x * scale.x, delta.y * scale.y, delta.z * scale.z))

    def project(point):
        point = world_to_camera_view(scene, scene.camera, local(point))
        return {'x': round(point.x * 100, 3), 'y': round((1 - point.y) * 100, 3)}

    floor['labels'] = [{**label, **project(label['position'])} for label in floor['labels']]
    for contact in floor.get('openings', []):
        contact.update(project(contact['marker_position']))
    lamps = {}
    for light in floor['lights']:
        lamps[light['key']] = []
        for emitter in light.get('emitters', [light]):
            data = bpy.data.lights.new('Circuit · ' + light['key'], 'AREA')
            data.shape = 'DISK'
            data.size = emitter.get('size', light.get('size', .75))
            data.spread = math.radians(emitter.get('spread', 180))
            data.energy = 0
            data.color = emitter.get('render_color', light.get('render_color', (1, .77, .5)))
            obj = bpy.data.objects.new(data.name, data)
            obj['floorplan_generated'] = True
            scene.collection.objects.link(obj)
            obj.location = local(emitter['position'])
            lamps[light['key']].append((obj, emitter.get('watts', light.get('watts', 100))))
        light.update(project(light['marker_position']))

    def set_circuit(key, enabled):
        for obj, watts in lamps[key]:
            obj.data.energy = watts if enabled else 0
        for material in bpy.data.materials:
            if material.get('fp_circuit') == key and material.use_nodes:
                material.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = material.get('fp_emission_on', 3.5) if enabled else 0

    def render(state):
        if os.getenv('FP_PROJECT_ONLY') == '1' or str(number) not in selected or (states is not None and state not in states):
            return
        scene.render.filepath = str(raw / f'floor-{number}-{state}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', number, state, flush=True)

    for light in floor['lights']:
        set_circuit(light['key'], False)
    render('base')
    for light in floor['lights']:
        set_circuit(light['key'], True)
        render(light['key'])
        set_circuit(light['key'], False)
    for light in floor['lights']:
        set_circuit(light['key'], True)
    if floor['lights']:
        render('all-on')
    for light in floor['lights']:
        set_circuit(light['key'], False)

PROJECTED.write_text(json.dumps(config, indent=2))
print('LIGHTING RENDERS COMPLETE — editable models were not saved or modified', flush=True)
