"""Validate the current project without any historical files.
--approved: require exact current approved file checksums.
--hosted: read/hash all active HA images. --published: also read dashboard via MCP.
These checks never publish configuration or actuate devices.
"""
import argparse
import hashlib
import json
import os
import numpy as np
from PIL import Image
from project_paths import ROOT, CONFIG, APPROVED, DASHBOARD, IMAGES, PREPARED, RENDERS, REPORTS, load_config, active_images
from dashboard_config import build_dashboard


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--approved', action='store_true')
parser.add_argument('--hosted', action='store_true')
parser.add_argument('--published', action='store_true')
args = parser.parse_args()
source, config, approved = load_config(), load(PREPARED), load(APPROVED)
assert [floor['floor'] for floor in source['floors']] == [1, 2, 3, 4]
for floor in source['floors']:
    assert (ROOT / floor['model_file']).is_file()
    key = str(floor['floor'])
    if key not in approved['bindings']:
        assert floor.get('model_only') and not args.approved, 'New entity bindings require review'
    bindings = approved['bindings'].get(key, {'lights': [], 'contacts': []})
    assert [light['entity'] for light in floor['lights']] == bindings['lights']
    assert [opening['entity'] for opening in floor.get('openings', [])] == bindings['contacts']
assert len({light['entity'] for floor in source['floors'] for light in floor['lights']}) == 13
assert sum(len(floor.get('openings', [])) for floor in source['floors']) == 2
first_light = source['floors'][0]['lights'][0]
assert len(source['floors'][0]['lights']) == 2
assert first_light['entity'] == 'light.first_floor_front_door_light'
assert first_light['name'] == 'Car & front door' and first_light['room'] == 'Garage & entrance'
assert len(first_light['emitters']) == 2 and 0 < sum(e['watts'] for e in first_light['emitters']) <= 60
assert first_light['emitters'][0]['position'][1] > -24.0 and first_light['emitters'][1]['position'][1] < -25.0
third = source['floors'][2]['lights']
assert [light['room'] for light in third[3:]] == ['Balcony', 'Corridor']
assert [light['entity'] for light in third[3:]] == ['switch.third_floor_corridor_light_1', 'switch.third_floor_corridor_light_2']
corridor_label = next(label for label in source['floors'][2]['labels'] if label['text'] == 'CORRIDOR')
assert third[4]['position'][:2] == corridor_label['position'][:2]
assert third[4]['watts'] == 65 and third[1]['watts'] == 120 and third[2]['watts'] == 100
fourth = source['floors'][3]
assert fourth['model_only'] and not fourth['lights'] and not fourth.get('openings')
if args.approved:
    assert len(approved['models']) == len(approved['bindings']) == 4
    for path, expected in approved['files'].items():
        assert digest(ROOT / path) == expected, 'Approved file changed: ' + path

models = load(REPORTS / 'models.json')
assert models['success'] and len(models['floors']) == 4
assert models['floors']['4']['checks']['model_only'] and models['floors']['4']['checks']['mapped_devices'] == 0
assert models['floors']['1']['checks']['garden_horizontal_at_rear_wall_under_stairs']
for floor in source['floors']:
    model = models['floors'][str(floor['floor'])]
    assert model['model_sha256'] == digest(ROOT / floor['model_file']), 'Rerun validate_models.py after editing a model'
files = active_images(config)
assert len(files) == len(set(files)) == 17
assert set(files) == {path.name for path in IMAGES.glob('*.png')}, 'Stale/unreferenced dashboard PNGs'
images = []
for name in files:
    path = IMAGES / name
    with Image.open(path) as image:
        assert image.size == (1400, 1400) and image.mode == 'RGBA', name
        image.verify()
    images.append({'file': name, 'sha256': digest(path)})
metrics = load(REPORTS / 'render-validation.json')
assert len([row for row in metrics if 'entity' in row]) == 13
for row in metrics:
    if 'entity' in row:
        assert row['mean_light_delta'] > .001 and row['lit_pixels'] > 1000 and row['single_state_mae'] < .003
    else:
        assert row['all_on_composite_mae'] < .06
base = np.asarray(Image.open(RENDERS / 'floor-3-base.png'), dtype=np.float64) / 255
colours = {}
for key in ('neutral', 'warm'):
    on = np.asarray(Image.open(RENDERS / f'floor-3-juan-{key}.png'), dtype=np.float64) / 255
    rgb = np.maximum(on[:, :, :3] - base[:, :, :3], 0)[base[:, :, 3] > .99].mean(axis=0)
    colours[key] = float(rgb[2] / rgb[0])
assert colours['neutral'] > colours['warm'] + .10
inputs = {'source_sha256': digest(CONFIG), 'prepared_sha256': digest(PREPARED),
          'runtime_sha256': digest(DASHBOARD / 'house-floorplan-card.js')}
preflight = load(REPORTS / 'verification-preflight.json')
assert preflight['success'] and not preflight['browser_errors'] and not preflight['live_roundtrips']
assert preflight['inputs'] == inputs, 'Rerun browser preflight after changing inputs'
assert len(preflight['screenshots']) == 20 and len(preflight['simulated_circuits']) == 13
assert [f['floor'] for f in preflight['model_only_floors']] == [4]
assert all(f['no_entity_bindings'] and f['no_device_controls'] and f['no_service_calls'] for f in preflight['model_only_floors'])
assert len(preflight['opening_sensors']) == 2 and len(preflight['all_off'][2]['targets']) == 5
assert preflight['balcony_corridor_mapping']['balcony'] == third[3]['entity']
assert preflight['balcony_corridor_mapping']['corridor'] == third[4]['entity']
report = {'success': True, 'approved_checksums_verified': args.approved, 'standalone_models_verified': 4,
          'total_lights': 13, 'read_only_contacts': 2, 'model_only_floors': [4], 'active_images': images,
          'juan_blue_red_ratios': colours, 'responsive_screenshots': 20, 'physical_device_operations': 0}
if args.hosted or args.published:
    import requests
    manifest = load(DASHBOARD / 'upload-manifest.json')
    url = os.environ['PI_MCP_HOMEASSISTANT_URL'].rstrip('/')
    assert manifest['server'] == url and set(manifest['images']) == set(files)
    for image in images:
        item = manifest['images'][image['file']]
        response = requests.get(url + item['url'], timeout=30)
        response.raise_for_status()
        assert hashlib.sha256(response.content).hexdigest() == image['sha256'] == item['sha256']
    report['hosted_image_hashes_verified'] = 17
if args.published:
    from mcp_client import HomeAssistantMCP
    remote = HomeAssistantMCP().call('ha_config_get_dashboard', {'url_path': 'house-3d', 'force_reload': True})
    assert remote['success'] and remote['config'] == load(DASHBOARD / 'dashboard.json')
    generated = build_dashboard(config, source, lambda name: manifest['images'][name]['url'])
    for view in generated['views']:
        matches = [v for v in remote['config']['views'] if v.get('path') == view['path']]
        assert len(matches) == 1 and matches[0]['cards'][0] == view['cards'][0]
    browser = load(REPORTS / 'verification-report.json')
    assert browser['success'] and browser['mode'] == 'deployed' and browser['inputs'] == inputs
    assert not browser['browser_errors'] and not browser['live_roundtrips']
    assert len(browser['screenshots']) == 20 and len(browser['simulated_circuits']) == 13
    assert browser['model_only_floors'] == preflight['model_only_floors']
    if args.approved:
        assert remote['config_hash'] == approved['dashboard_hash']
    report.update(published=True, dashboard_hash=remote['config_hash'], browser_errors=0)
(REPORTS / 'project-validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != 'active_images'}, indent=2))
