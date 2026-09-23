"""Derive screen-blended PNG layers without double-counting ambient light."""
import json
import numpy as np
from PIL import Image
from project_paths import RENDERS, IMAGES, PREVIEWS, REPORTS, PROJECTED, PREPARED, ensure_output_dirs

ensure_output_dirs()
config = json.loads(PROJECTED.read_text())
report = []
for floor in config['floors']:
    n = floor['floor']
    prefix = f'floor-{n}'
    base_image = Image.open(RENDERS / f'{prefix}-base.png').convert('RGBA')
    base = np.asarray(base_image, dtype=np.float32) / 255
    base_image.save(IMAGES / f'{prefix}-base.png', optimize=True)
    composite = base[:, :, :3].copy()
    alpha = base[:, :, 3:4]
    floor['image_file'] = f'{prefix}-base.png'
    for light in floor['lights']:
        on = np.asarray(Image.open(RENDERS / f'{prefix}-{light["key"]}.png').convert('RGBA'), dtype=np.float32) / 255
        # Screen(base, layer) = 1 - (1-base)*(1-layer).
        layer = np.clip((on[:, :, :3] - base[:, :, :3]) / np.maximum(1 - base[:, :, :3], 1/255), 0, 1)
        mask = (np.max(layer, axis=2, keepdims=True) > .008) * alpha
        layer[mask[:, :, 0] == 0] = 0
        rgba = np.concatenate([layer, mask], axis=2)
        name = f'{prefix}-{light["key"]}-light.png'
        Image.fromarray(np.rint(rgba * 255).astype('uint8')).save(IMAGES / name, optimize=True)
        light['image_file'] = name
        if light['key'] in ('bathroom-2', 'bathroom-3'):
            light['compact_hide'] = True
        composite = 1 - (1 - composite) * (1 - layer * mask)
        single = 1 - (1 - base[:, :, :3]) * (1 - layer * mask)
        area = alpha[:, :, 0] > .99
        report.append({'floor': n, 'entity': light['entity'], 'lit_pixels': int((mask[:, :, 0] > .9).sum()),
                       'mean_light_delta': float((on[:, :, :3] - base[:, :, :3])[area].mean()),
                       'single_state_mae': float(np.abs(single - on[:, :, :3])[area].mean()),
                       'bytes': (IMAGES / name).stat().st_size})
    result = np.concatenate([composite, alpha], axis=2)
    Image.fromarray(np.rint(result * 255).astype('uint8')).save(PREVIEWS / f'{prefix}-composite-all-on.png', optimize=True)
    truth = (np.asarray(Image.open(RENDERS / f'{prefix}-all-on.png').convert('RGBA'), dtype=np.float32) / 255
             if floor['lights'] else base)
    report.append({'floor': n, 'all_on_composite_mae': float(np.abs(composite - truth[:, :, :3])[alpha[:, :, 0] > .99].mean())})
PREPARED.write_text(json.dumps(config, indent=2))
(REPORTS / 'render-validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
