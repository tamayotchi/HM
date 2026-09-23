"""Blender-only, read-only fingerprints of geometry and visual settings.
File paths and timestamps are deliberately excluded. Packed texture bytes,
mesh topology/UVs, shaders, camera, lamps and visibility are included.
"""
import array
import hashlib
import json
import bpy


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def value(v):
    if isinstance(v, bpy.types.ID):
        return {'id': v.name, 'type': v.__class__.__name__}
    if isinstance(v, float):
        return round(v, 7)
    if isinstance(v, (str, int, bool)) or v is None:
        return v
    try:
        return [value(x) for x in v]
    except TypeError:
        return str(type(v))


def settings(obj):
    result = {}
    for prop in obj.bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.is_readonly or prop.type in {'COLLECTION', 'POINTER'}:
            continue
        try:
            result[prop.identifier] = value(getattr(obj, prop.identifier))
        except (AttributeError, TypeError):
            pass
    return result


def tree_data(tree):
    if not tree:
        return None
    nodes = []
    for node in sorted(tree.nodes, key=lambda n: n.name):
        row = {'name': node.name, 'type': node.bl_idname,
               'inputs': [(s.identifier, value(s.default_value)) for s in node.inputs if hasattr(s, 'default_value')]}
        for key in ('operation', 'blend_type', 'interpolation', 'extension', 'projection', 'distribution'):
            if hasattr(node, key):
                row[key] = value(getattr(node, key))
        if getattr(node, 'image', None):
            image = node.image
            assert image.packed_file, f'Unpacked shader texture: {image.name}'
            row['image'] = hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
            row['colour_space'] = image.colorspace_settings.name
        if getattr(node, 'node_tree', None):
            row['group'] = tree_data(node.node_tree)
        nodes.append(row)
    return {'nodes': nodes, 'links': sorted((l.from_node.name, l.from_socket.identifier,
                                             l.to_node.name, l.to_socket.identifier) for l in tree.links)}


def buffer_hash(collection, attribute, width, typecode='f'):
    data = array.array(typecode, [0]) * (len(collection) * width)
    collection.foreach_get(attribute, data)
    return hashlib.sha256(data.tobytes()).hexdigest()


def fingerprint(scene, objects=None):
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    selected = scene.objects if objects is None else objects
    objects = []
    for obj in sorted(selected, key=lambda o: o.name):
        row = {'name': obj.name, 'type': obj.type,
               'matrix': [value(r) for r in obj.matrix_world],
               'visibility': {k: getattr(obj, k) for k in ('hide_render', 'visible_camera', 'visible_shadow',
                            'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter')},
               'modifiers': [settings(m) for m in obj.modifiers]}
        if obj.type == 'MESH':
            mesh = obj.data
            row['mesh'] = {
                'vertices': buffer_hash(mesh.vertices, 'co', 3),
                'loops': buffer_hash(mesh.loops, 'vertex_index', 1, 'i'),
                'polygons': [(p.loop_start, p.loop_total, p.material_index, p.use_smooth) for p in mesh.polygons],
                'uv': [(uv.name, buffer_hash(uv.data, 'uv', 2)) for uv in mesh.uv_layers],
                'materials': [{'name': m.name, 'diffuse': value(m.diffuse_color), 'nodes': tree_data(m.node_tree)}
                              if m else None for m in mesh.materials]}
        elif obj.type in {'LIGHT', 'CAMERA'}:
            row['data'] = settings(obj.data)
        objects.append(row)
    return {'scene': scene.name, 'objects': len(objects),
            'object_digest': digest(objects),
            'world_digest': digest(tree_data(scene.world.node_tree)),
            'camera': scene.camera.name,
            'render': {key: getattr(scene.render, key) for key in
                       ('engine', 'resolution_x', 'resolution_y', 'resolution_percentage', 'film_transparent')},
            'view': {key: getattr(scene.view_settings, key) for key in
                     ('view_transform', 'look', 'exposure', 'gamma')}}
