"""Generate the three public README previews offline, without HA access.
Only the selected PNG light layers are composited; no UI labels or live states.
This private helper overwrites the same three public images on each run.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / 'dashboard/images'
OUTPUT = ROOT / 'docs/images'
OUTPUT.mkdir(parents=True, exist_ok=True)
PREVIEWS = [
    (1, ['mini-kitchen'], 'first-floor-mini-kitchen.png'),
    (2, ['bathroom-1', 'bathroom-2', 'bathroom-3'], 'second-floor-bathroom.png'),
    (3, ['corridor-2'], 'third-floor-corridor.png'),
]
report = {'simulated': True, 'home_assistant_requests': 0, 'physical_device_operations': 0, 'images': []}
for floor, circuits, output_name in PREVIEWS:
    base_path = IMAGES / f'floor-{floor}-base.png'
    with Image.open(base_path) as image:
        base = np.asarray(image.convert('RGBA'), dtype=np.float64) / 255
    rgb = base[:, :, :3].copy()
    inputs = [base_path]
    for circuit in circuits:
        path = IMAGES / f'floor-{floor}-{circuit}-light.png'
        inputs.append(path)
        with Image.open(path) as image:
            layer = np.asarray(image.convert('RGBA'), dtype=np.float64) / 255
        rgb = 1 - (1 - rgb) * (1 - layer[:, :, :3] * layer[:, :, 3:4])
    background = np.array([12, 20, 35], dtype=np.float64) / 255
    rgb = rgb * base[:, :, 3:4] + background * (1 - base[:, :, 3:4])
    # Fresh pixel-only image: no EXIF, filenames, comments, UI or inherited metadata.
    public = Image.fromarray(np.rint(np.clip(rgb, 0, 1) * 255).astype('uint8'))
    public = public.resize((1000, 1000), Image.Resampling.LANCZOS)
    target = OUTPUT / output_name
    public.save(target, optimize=True)
    with Image.open(target) as image:
        assert image.mode == 'RGB' and image.size == (1000, 1000) and not image.info
    report['images'].append({'file': str(target.relative_to(ROOT)), 'floor': floor, 'only_lit_circuits': circuits,
                             'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                             'inputs': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}})
reports = ROOT / 'build/reports'
reports.mkdir(parents=True, exist_ok=True)
(reports / 'readme-images.json').write_text(json.dumps(report, indent=2))
for image in report['images']:
    print(image['file'], '— only', ', '.join(image['only_lit_circuits']))
