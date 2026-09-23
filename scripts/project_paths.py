"""Shared project paths. No machine-specific absolute paths or historical inputs."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/lighting-map.json'
DASHBOARD = ROOT / 'dashboard'
IMAGES = DASHBOARD / 'images'
BUILD = ROOT / 'build'
RENDERS = BUILD / 'renders'
PREVIEWS = BUILD / 'previews'
REPORTS = BUILD / 'reports'
PROJECTED = BUILD / 'projected-lighting-map.json'
PREPARED = BUILD / 'floorplan-config.json'
APPROVED = ROOT / 'config/approved-state.json'


def load_config():
    return json.loads(CONFIG.read_text())


def ensure_output_dirs():
    for path in (IMAGES, RENDERS, PREVIEWS, REPORTS, BUILD / 'logs'):
        path.mkdir(parents=True, exist_ok=True)


def active_images(config):
    return [name for floor in config['floors']
            for name in [floor['image_file'], *[light['image_file'] for light in floor['lights']]]]
