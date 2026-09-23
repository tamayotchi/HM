"""Offline tests: config generation, current file layout and safe publisher dry runs."""
import copy
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard_config import build_dashboard
from project_paths import ROOT, CONFIG, DASHBOARD, PREPARED, active_images


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(CONFIG.read_text())
        self.config = json.loads(PREPARED.read_text())
        self.manifest = json.loads((DASHBOARD / 'upload-manifest.json').read_text())
        self.published = json.loads((DASHBOARD / 'dashboard.json').read_text())

    def generate(self, config=None):
        return build_dashboard(config or self.config, self.source, lambda name: self.manifest['images'][name]['url'])

    def test_current_cards_match_published(self):
        for desired in self.generate()['views']:
            actual = next(v for v in self.published['views'] if v['path'] == desired['path'])
            self.assertEqual(actual['cards'][0], desired['cards'][0])

    def test_overview_reuses_all_four_floors(self):
        generated = self.generate()
        overview = next(v for v in generated['views'] if v['path'] == 'all-floors')['cards'][0]
        self.assertEqual(overview['type'], 'custom:house-overview-card')
        self.assertEqual(len(overview['floors']), 4)
        for view, floor in zip(generated['views'][:4], overview['floors']):
            expected = copy.deepcopy(view['cards'][0])
            expected.pop('type')
            expected['navigation_path'] = '/house-3d/' + view['path']
            self.assertEqual(floor, expected)
        self.assertEqual(sum(len(f['lights']) for f in overview['floors']), 13)
        self.assertTrue(overview['floors'][3]['model_only'])
        self.assertNotIn('callService', (DASHBOARD / 'house-overview-card.js').read_text())

    def test_duplicate_entity_rejected(self):
        config = copy.deepcopy(self.config)
        config['floors'][2]['lights'][0]['entity'] = config['floors'][0]['lights'][0]['entity']
        with self.assertRaises(AssertionError):
            self.generate(config)

    def test_contact_cannot_be_used_as_light(self):
        config = copy.deepcopy(self.config)
        config['floors'][0]['lights'][0]['entity'] = 'binary_sensor.first_floor_front_door_sensor'
        with self.assertRaises(AssertionError):
            self.generate(config)

    def test_only_active_images_retained(self):
        names = active_images(self.config)
        self.assertEqual(len(set(names)), 17)
        self.assertEqual(set(names), set(self.manifest['images']))
        self.assertEqual(set(names), {p.name for p in (DASHBOARD / 'images').glob('*.png')})

    def test_four_models_not_linked_to_a_revision_path(self):
        self.assertNotIn('scene_file', self.source)
        self.assertEqual(len(self.source['floors']), 4)
        for floor in self.source['floors']:
            model = ROOT / floor['model_file']
            self.assertTrue(model.is_file())
            self.assertEqual(model.name, 'model.blend')
            self.assertEqual(model.parent.parent.name, 'floors')

    def test_first_floor_shared_light_is_subdued_and_keeps_its_entity(self):
        lights = self.source['floors'][0]['lights']
        self.assertEqual(len(lights), 2)
        self.assertEqual(lights[0]['entity'], 'light.first_floor_front_door_light')
        self.assertEqual(lights[0]['room'], 'Garage & entrance')
        self.assertEqual(lights[0]['name'], 'Car & front door')
        self.assertLessEqual(sum(e['watts'] for e in lights[0]['emitters']), 60)

    def test_current_third_floor_roles(self):
        lights = self.generate()['views'][2]['cards'][0]['lights']
        self.assertEqual([light['room'] for light in lights[3:]], ['Balcony', 'Corridor'])
        self.assertEqual([light['name'] for light in lights[1:3]], ['Light 1 · neutral', 'Light 2 · warm'])
        self.assertTrue(all(not light.get('compact_hide') for light in lights))

    def test_corrected_corridor_position_and_softer_juan_warm(self):
        floor = self.source['floors'][2]
        label = next(label for label in floor['labels'] if label['text'] == 'CORRIDOR')
        self.assertEqual(floor['lights'][4]['position'][:2], label['position'][:2])
        self.assertEqual(floor['lights'][4]['watts'], 65)
        self.assertEqual(floor['lights'][1]['watts'], 120)
        self.assertEqual(floor['lights'][2]['watts'], 100)

    def test_fourth_floor_is_model_only(self):
        fourth = self.generate()['views'][3]
        self.assertEqual(fourth['path'], 'fourth-floor')
        card = fourth['cards'][0]
        self.assertTrue(card['model_only'])
        self.assertEqual(card['lights'], [])
        self.assertFalse(card.get('openings'))
        self.assertEqual(sum(len(f['lights']) for f in self.source['floors']), 13)
        config = copy.deepcopy(self.config)
        config['floors'][3]['lights'] = [config['floors'][0]['lights'][0]]
        with self.assertRaisesRegex(AssertionError, 'Model-only'):
            self.generate(config)

    def publisher_dry_run(self, changed=False, add_fourth=False, authorize=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dashboard = root / 'dashboard'
            dashboard.mkdir()
            local = copy.deepcopy(self.published)
            if changed:
                local['views'][2]['cards'][0]['note'] += ' Local test only.'
            (dashboard / 'dashboard.json').write_text(json.dumps(local))
            calls = []
            live = copy.deepcopy(self.published)
            if add_fourth:
                live['views'] = [v for v in live['views'] if v['path'] != 'fourth-floor']
            remote = {'success': True, 'config_hash': 'test-hash', 'config': live}
            class FakeMCP:
                def call(self, name, args):
                    calls.append(name)
                    if name != 'ha_config_get_dashboard':
                        raise AssertionError('Dry run attempted a write: ' + name)
                    return copy.deepcopy(remote)
            paths = types.ModuleType('project_paths')
            paths.ROOT, paths.DASHBOARD, paths.REPORTS = root, dashboard, root / 'build/reports'
            mcp = types.ModuleType('mcp_client')
            mcp.HomeAssistantMCP = FakeMCP
            output = io.StringIO()
            argv = ['publish_dashboard_cards.py', '--dry-run']
            if add_fourth and authorize:
                argv += ['--allow-add-view', 'fourth-floor']
            with patch.dict(sys.modules, {'project_paths': paths, 'mcp_client': mcp}), \
                 patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as exit_info:
                    runpy.run_path(str(ROOT / 'scripts/publish_dashboard_cards.py'), run_name='__main__')
                self.assertEqual(exit_info.exception.code, 0)
            self.assertEqual(calls, ['ha_config_get_dashboard'])
            self.assertFalse((root / 'build').exists(), 'Dry run created a snapshot/report')
            return json.loads(output.getvalue())

    def test_model_only_view_addition_is_explicit_and_narrow(self):
        result = self.publisher_dry_run(add_fourth=True)
        self.assertEqual(result['added_views'], ['fourth-floor'])
        self.assertEqual(len(result['patch']), 1)
        self.assertEqual(result['patch'][0]['op'], 'add')
        self.assertEqual(result['patch'][0]['path'], '/views/-')

    def test_view_addition_without_permission_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'not explicitly authorized'):
            self.publisher_dry_run(add_fourth=True, authorize=False)

    def test_noop_publish_dry_run_is_read_only(self):
        self.assertEqual(self.publisher_dry_run()['patch'], [])

    def test_changed_publish_dry_run_only_plans_third_floor_card(self):
        result = self.publisher_dry_run(changed=True)
        self.assertEqual(result['changed_floor_cards'], ['third-floor'])
        self.assertEqual(result['patch'][0]['path'], '/views/2/cards/0')


if __name__ == '__main__':
    unittest.main()
