"""Read-only Blender checks for the current standalone models.
Pass -- --approved to also require the exact user-approved visual fingerprints.
No old model, revision directory or backup is needed.
"""
import bpy
import hashlib
import json
import os
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import ROOT, APPROVED, REPORTS, load_config, ensure_output_dirs
from model_fingerprint import fingerprint


def vertices(objects):
    return [obj.matrix_world @ Vector(point) for obj in objects for point in obj.bound_box]


def mesh_tree(objects):
    verts, faces = [], []
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        start = len(verts)
        verts.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        faces.extend(tuple(start + i for i in face.vertices) for face in mesh.polygons)
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False)


def first_floor(scene):
    car = [obj for obj in scene.objects if obj.name.startswith('BMW X4 · ')]
    assert len(car) == 114 and not any(obj.name.startswith('2014 Mazda') for obj in scene.objects)
    points = vertices(car)
    dimensions = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
    assert all(abs(a-b) < 1e-5 for a, b in zip(dimensions, [2.164246333380978, 4.752, 1.6252919279023599]))
    assert all(abs(a-b) < 1e-6 for a, b in zip(scene['bathroom_clear_dimensions_metres'], [2.1, 1.0]))
    floor = scene.objects['V3 F1 · Bathroom stone floor']
    assert abs(floor.dimensions.x - 2.1) < 1e-5 and abs(floor.dimensions.y - 1) < 1e-5
    assert scene['bathroom_door_type'] == 'sliding' and not scene['mini_kitchen_has_door']
    for mat in bpy.data.materials:
        if mat.name.startswith('BMW ACCA'):
            assert mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value == 0
    ignore = {'Floor 1 display plinth', 'Grupo#27:geometry.001', 'Grupo#24:geometry.001', 'Grupo#25:geometry.001'}
    car_tree = mesh_tree(car)
    collisions = [obj.name for obj in scene.objects if obj.type == 'MESH' and obj not in car
                  and obj.name not in ignore and len(obj.data.polygons) and car_tree.overlap(mesh_tree([obj]))]
    assert not collisions, collisions
    garden = [obj for obj in scene.objects if obj.name.startswith('V3 F1 · Garden')]
    assert len(garden) == 165
    planter = scene.objects['V3 F1 · Garden low stone planter']
    planter_points = vertices([planter])
    planter_xy = [max(p[i] for p in planter_points) - min(p[i] for p in planter_points) for i in (0, 1)]
    assert abs(planter_xy[0] - 1.66) < 1e-5 and abs(planter_xy[1] - .84) < 1e-5
    garden_points = [point + Vector((23, -22.85, 0)) for point in vertices(garden)]
    garden_bounds = [[min(p[i] for p in garden_points) for i in range(3)],
                     [max(p[i] for p in garden_points) for i in range(3)]]
    assert 23.6 < garden_bounds[0][0] < 23.7 and 25.3 < garden_bounds[1][0] < 25.4
    assert -19.6 < garden_bounds[0][1] < -19.4 and -18.75 < garden_bounds[1][1] < -18.65
    garden_tree = mesh_tree(garden)
    garden_collisions = [obj.name for obj in scene.objects if obj.type == 'MESH' and obj not in garden
                         and obj.name not in ignore and len(obj.data.polygons) and garden_tree.overlap(mesh_tree([obj]))]
    assert not garden_collisions, garden_collisions
    return {'bmw_meshes': len(car), 'bmw_dimensions_metres': dimensions, 'car_intersections': collisions,
            'garden_horizontal_at_rear_wall_under_stairs': True, 'garden_plan_bounds': garden_bounds,
            'garden_intersections': garden_collisions,
            'bathroom_metres': [2.1, 1.0], 'sliding_door_open_kitchen': True, 'surveyed_clearance_guarantee': False}


def second_floor(scene):
    grey = bpy.data.materials['V2 · Cinza cabinetry']
    wardrobes = [obj for obj in scene.objects if obj.type == 'MESH'
                 and obj.name.startswith(('V2 · Front wardrobe', 'V2 · Rear wardrobe')) and 'handle' not in obj.name]
    assert len(wardrobes) == 6 and all(obj.data.materials[0] == grey for obj in wardrobes)
    assert any(obj not in wardrobes and obj.type == 'MESH' and grey in obj.data.materials[:] for obj in scene.objects)
    assert scene['bedroom_door_hinge_side'].startswith('right')
    origin, scale = Vector((2.65, 3.85, 0)), Vector(scene['coordinate_scale'])
    floors = [obj for obj in scene.objects if obj.type == 'MESH' and len(obj.data.polygons)
              and obj.name.startswith(('V2 · Structural floor slab', 'V2 · Presentation base', 'V2 · Porcelain tile'))]
    graph = bpy.context.evaluated_depsgraph_get()
    trees = [(obj, BVHTree.FromObject(obj, graph)) for obj in floors]
    def floor_hits(x, y):
        delta = Vector((x, y, .12)) - origin
        point = Vector((delta.x * scale.x, delta.y * scale.y, delta.z))
        return [obj.name for obj, tree in trees if tree.ray_cast(obj.matrix_world.inverted() @ point,
                (obj.matrix_world.inverted().to_3x3() @ Vector((0, 0, -1))).normalized(), 1.0)[0] is not None]
    for ix in range(15):
        for iy in range(17):
            assert not floor_hits(3.135 + ix*(5.085-3.135)/14, 5.405 + iy*(7.75-5.405)/16)
    assert floor_hits(4.5, 5.15) and floor_hits(2.8, 6.0)
    lower = [obj for obj in scene.objects if 'To floor below' in obj.name]
    assert len(lower) > 40 and min(point.z for point in vertices(lower)) < -2.6
    return {'wardrobe_panels_exact_kitchen_grey': 6, 'door_hinge': 'right entering from hall',
            'empty_stairwell_ray_samples': 255, 'approach_landing_preserved': True, 'lower_stairs_present': True}


def third_floor(scene):
    oak = bpy.data.materials['V2 · Natural oak joinery']
    leaves = [obj for obj in scene.objects if 'wardrobe sliding leaf' in obj.name]
    assert len(leaves) == 4 and all(obj.data.materials[0] == oak for obj in leaves)
    assert len([obj for obj in scene.objects if 'office chair upholstered seat' in obj.name]) == 2
    assert len([obj for obj in scene.objects if 'office chair five star leg' in obj.name]) == 10
    assert not any('stool' in obj.name.lower() or 'bench' in obj.name.lower() for obj in scene.objects)
    parapets = [obj for obj in scene.objects if 'Balcony white ' in obj.name and 'half wall' in obj.name]
    assert len(parapets) == 3 and all(obj.data.materials[0].name == 'F3 · White balcony plaster' for obj in parapets)
    desk = scene.objects['F3 · Juan desk tabletop']
    assert desk.data.materials[0].name == 'F3 · Juan black desk'
    wall = scene.objects['F3 · Juan window left white wall']
    assert wall.data.materials[0] == bpy.data.materials['V2 · Warm white plaster']
    assert abs(wall.dimensions.z - .92) < 1e-5 and wall.visible_camera
    assert scene['balcony_light_entity'] == 'switch.third_floor_corridor_light_1'
    assert scene['corridor_light_entity'] == 'switch.third_floor_corridor_light_2'
    assert scene['juan_neutral_entity'] == 'switch.juan_room_light_1'
    assert scene['juan_warm_entity'] == 'switch.juan_room_light_2'
    origin, scale = Vector(scene['coordinate_origin']), Vector(scene['coordinate_scale'])
    def bounds(objects):
        points = vertices(objects)
        return [[min(p[i]/scale[i] + origin[i] for p in points) for i in range(3)],
                [max(p[i]/scale[i] + origin[i] for p in points) for i in range(3)]]
    glass = bounds([scene.objects['F3 · Juan window glass']])
    assert glass[0][0] > 1.515 and glass[1][0] < 2.78
    bed = [obj for obj in scene.objects if obj.type == 'MESH' and obj.name.startswith('F3 · Juan · ')]
    desk_chair = [obj for obj in scene.objects if obj.type == 'MESH' and obj.name.startswith(
        ('F3 · Juan desk ', 'F3 · Juan office chair', 'F3 · Juan chair '))]
    assert len(desk_chair) > 20
    bed_bounds, desk_bounds = bounds(bed), bounds([desk])
    chair_bounds = bounds([scene.objects['F3 · Juan office chair upholstered seat']])
    assert bed_bounds[1][0] < desk_bounds[0][0] and bed_bounds[1][0] < chair_bounds[0][0]
    assert bed_bounds[1][1] < 3.88 and desk_bounds[1][1] < 3 and chair_bounds[1][1] < 3
    boundaries = [obj for obj in scene.objects if obj.type == 'MESH' and obj.name.startswith(
        ('F3 · Left exterior', 'F3 · Front bedroom right side', 'F3 · Juan solid wall below window',
         'F3 · Juan window left', 'F3 · Juan window right', 'F3 · Juan wardrobe'))]
    assert not mesh_tree([scene.objects['F3 · Front bedroom open door']]).overlap(mesh_tree(bed + desk_chair))
    assert not mesh_tree(bed).overlap(mesh_tree(desk_chair))
    assert not mesh_tree(bed + desk_chair).overlap(mesh_tree(boundaries))
    return {'oak_sliding_leaves': 4, 'office_chairs': 2, 'white_balcony_half_walls': 3,
            'bed_bottom_left': True, 'black_desk_chair_bottom_right': True,
            'window_left_white_right_glazed': True, 'furniture_intersections': [],
            'balcony_light_1_corridor_light_2': True, 'juan_neutral_1_warm_2': True}


def fourth_floor(scene):
    assert scene.get('model_only') and scene['mapped_entities_json'] == '[]'
    assert not any(obj.name.startswith('Circuit · ') or obj.get('floorplan_generated') for obj in scene.objects)
    assert all(obj.name.startswith('F4 · ') for obj in scene.objects if obj.type == 'MESH')
    origin, scale = Vector(scene['coordinate_origin']), Vector(scene['coordinate_scale'])
    def bounds(objects):
        points = vertices(objects)
        return [[min(p[i]/scale[i] + origin[i] for p in points) for i in range(3)],
                [max(p[i]/scale[i] + origin[i] for p in points) for i in range(3)]]
    sink = [obj for obj in scene.objects if obj.name.startswith('F4 · Laundry sink')]
    washer = [obj for obj in scene.objects if obj.name.startswith('F4 · Washing machine')]
    assert len(sink) >= 15 and len(washer) >= 12
    sink_bounds, washer_bounds = bounds(sink), bounds(washer)
    assert sink_bounds[1][0] < 1.5 and sink_bounds[0][1] > 6.8
    assert washer_bounds[1][0] < 1 and washer_bounds[1][1] < sink_bounds[0][1]
    assert not mesh_tree(sink).overlap(mesh_tree(washer))
    stairs = [obj for obj in scene.objects if obj.name.startswith('F4 · Descending stairs')]
    assert len(stairs) > 40
    stair_points = vertices(stairs)
    assert max(p.z for p in stair_points) < .001 and min(p.z for p in stair_points) < -2.6
    surfaces = [obj for obj in scene.objects if obj.name.startswith(('F4 · Structural laundry slab', 'F4 · Laundry floor surface'))]
    tree = mesh_tree(surfaces)
    def floor_hit(x,y):
        p = Vector((x,y,.12)) - origin
        return tree.ray_cast(Vector((p.x*scale.x,p.y*scale.y,p.z)), Vector((0,0,-1)), 1)[0]
    for ix in range(15):
        for iy in range(17):
            assert floor_hit(3.135+ix*(5.085-3.135)/14,5.405+iy*(7.75-5.405)/16) is None
    assert floor_hit(3.65,5.1) is not None and floor_hit(1.7,6.3) is not None
    roof = [obj for obj in scene.objects if obj.name.startswith('F4 · Roof tile r')]
    assert len(roof) == 288 and bounds(roof)[1][1] < 4.3
    assert all(abs(a-b)<1e-6 for a,b in zip(scene['laundry_clear_dimensions_metres'], [4.74,3.21]))
    return {'model_only': True, 'mapped_devices': 0, 'laundry_sink_top_left': True,
            'washing_machine_directly_below_sink': True, 'utility_intersections': [],
            'stairs_descend_to_floor_3_only': True, 'empty_stairwell_ray_samples': 255,
            'approach_landing_preserved': True, 'lower_front_roof_tiles': len(roof),
            'finishes_and_dimensions_illustrative': True}


ensure_output_dirs()
approved = json.loads(APPROVED.read_text())
checks = {1: first_floor, 2: second_floor, 3: third_floor, 4: fourth_floor}
report = {'success': True, 'approved_fingerprints_checked': '--approved' in sys.argv, 'floors': {}}
for floor in load_config()['floors']:
    path = Path(os.environ.get(f'FP_MODEL_{floor["floor"]}', str(ROOT / floor['model_file'])))
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert len(bpy.data.scenes) == 1 and not bpy.data.libraries
    scene = bpy.data.scenes[floor['scene']]
    current = fingerprint(scene)
    if '--approved' in sys.argv:
        assert current == approved['models'][str(floor['floor'])], f'Approved visual data changed: {path}'
    for image in bpy.data.images:
        if image.source == 'FILE' and image.type == 'IMAGE':
            assert image.packed_file, f'External texture dependency: {image.name}'
    details = checks[floor['floor']](scene)
    report['floors'][str(floor['floor'])] = {'model_file': floor['model_file'], 'fingerprint': current,
                                          'model_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                          'self_contained': True, 'checks': details}
(REPORTS / 'models.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
