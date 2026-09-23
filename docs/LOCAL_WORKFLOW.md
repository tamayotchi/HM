# House · 3D · private working guide

**Local only:** this guide, models, operational scripts and live configuration are excluded from the public file allowlist. The root README is the public showcase. Regenerate its three offline previews with `.venv/bin/python scripts/prepare_readme.py`; this makes no HA requests. The root `hm` launcher includes its own credential-free `.pi/` configuration.

An editable Blender floor per folder, plus a lightweight Home Assistant dashboard.
**The files here are the approved current house—not a collection of revisions.**

## Start here

Open the floor you want to edit in Blender:

```text
floors/
├── first-floor/
│   ├── model.blend        ← BMW, garage, mini kitchen, bathroom, stairs/garden
│   ├── README.md          ← current layout and important constraints
│   └── references/        ← original plan and stair photograph
├── second-floor/
│   ├── model.blend        ← Lorena, kitchen/bar, living room, bathroom
│   ├── README.md
│   └── references/
├── third-floor/
│   ├── model.blend        ← Alejandro, Juan, corridor, bathroom, balcony
│   ├── README.md
│   └── references/
└── fourth-floor/
    ├── model.blend        ← laundry sink, washing machine, descending stairs, roof
    ├── README.md
    └── references/
```

Each `model.blend` contains **one floor scene**, its geometry/materials, packed textures, camera, ambient lighting and, where configured, saved circuit lamps. No other Blender file, historical model or linked library is required. Circuit lamps are saved off; that does not turn physical devices off.

These four files are the **authoritative editable models**. There is no old-revision builder chain. Editing one floor does not alter another; coordinate shared stair/finish changes deliberately when needed. The original SketchUp remains untouched at `/home/tamayotchi/Downloads/Modelo completo.skp`; normal work does not depend on it.

## Project organization

| Location | Responsibility |
|---|---|
| `floors/` | Editable models, current layout notes and reference photographs/plans |
| `config/lighting-map.json` | Model paths; entity IDs, circuit colours/emitters, hotspots, labels and contacts |
| `config/approved-state.json` | Small checksum/visual-fingerprint record of the current approved house; no old model copies |
| `dashboard/house-floorplan-card.js` | Dependency-free individual-floor browser card |
| `dashboard/house-overview-card.js` | Read-only 2×2 landscape monitor, live layers, fullscreen and floor navigation |
| `dashboard/images/` | Exactly 17 active PNGs: 4 backgrounds + 13 light layers |
| `dashboard/dashboard.json` | Current published dashboard configuration |
| `dashboard/upload-manifest.json` | Current hosted image IDs, hashes and resource ID |
| `build/renders/` | Current raw base, per-circuit and all-on Blender renders |
| `build/previews/` | Current composites and browser screenshots |
| `build/reports/` | Current validation, read-back and publication results |
| `build/logs/` | Latest command logs |
| `scripts/` | Render, prepare, check and publish tools |
| `scripts/modeling/` | Optional shared-stair modelling helper, not an automatic floor rebuilder |
| `docs/bmw-x4/` | Small attribution/licence and publisher metadata records; no model binaries |

`build/` is generated working data, not an alternative model source. It can be regenerated, but deleting raw renders requires a full render before asset preparation. Old revisions, rejected models, unused candidates, redundant `.blend1` files and draft previews have been removed. There is no historical `source/` or `backups/` tree. The redundant `resources/` tree and BMW import scripts were also removed: the BMW is fully embedded in the first-floor model.

## How it works

```text
floors/*/model.blend + config/lighting-map.json
                   │
                   ▼
         scripts/render_lighting.py
                   │
                   ▼
            build/renders/*.png
                   │
                   ▼
         scripts/prepare_assets.py
                   │
                   ▼
            dashboard/images/
                   │
             explicit deployment
                   ▼
         Home Assistant hosts the images
         Live entity states select layers
```

This is fixed-camera rendering, not orbitable WebGL. Blender/the computer need not be running after deployment. A geometry/camera change requires rerendering the affected floor. Lighting layers approximate combinations using screen compositing rather than rendering live.

**Editing rules:**
- Edit geometry, materials, camera and ambient lighting in the appropriate `model.blend`, then save that same file.
- Edit circuit emitter positions/powers/colours and HA bindings in `config/lighting-map.json`. Lamps named `Circuit · …` are regenerated in memory from this file; moving only their saved Blender copies will not change the next render.
- Map coordinates use each floor's `coordinate_origin`/`coordinate_scale`; first-floor defaults are `(23,-22.85,0)` and `(1,1,1)`. Labels may use explicit percentage `screen_position` overrides.
- Rendering never saves over the editable `.blend` files. No script silently recreates a floor from an older snapshot.
- Preserve asset attribution and packed textures. BMW attribution/licensing notes are in `docs/bmw-x4/README.md`; there are no external BMW resource dependencies.

## Current Home Assistant dashboard

- **[All floors · tablet overview](http://192.168.1.13:8123/house-3d/all-floors)** — 2×2 landscape; tap **Full screen** to hide HA chrome. Tap a floor for its existing controls. All 13 lighting layers and both contacts update live; fourth floor remains model-only. No automatic cycling or direct device toggles. Latest-state timestamp does not identify who operated a switch.
- [First floor](http://192.168.1.13:8123/house-3d/first-floor)
- [Second floor](http://192.168.1.13:8123/house-3d/second-floor)
- [Third floor](http://192.168.1.13:8123/house-3d/third-floor)
- [Fourth floor](http://192.168.1.13:8123/house-3d/fourth-floor) — model only, no connected devices.
- Sidebar: **House · 3D**. Current verified hash: **`85c39698d018ed2a`**.
- All four floors are implemented. Floor 4 has one static daylit image and no lights, sensors, counters, All off button or on/off legend.
- The overview is an additional panel view backed by a separate resource (`overview_resource_id` in the manifest). Original floor view configurations are unchanged. Both card runtimes now use larger, model-fitted renders. The generator derives overview assets/bindings from the individual views so future image updates stay consistent.
- **Render-first layout:** overview status lists are now behind each floor’s **Status** button, not permanent sidebars. Individual floors have bulbs/door indicators directly on the model, with **Controls**, **All off**, **Labels**, **Full screen**, and **− / Fit / +** inside the render panel. **Controls** opens an in-panel drawer; model notes/attribution are under **About this model**. Both cards fit the nontransparent image bounds without altering assets; zoomed views support drag-to-pan. Fit resets zoom/pan. The dashboard config and all 17 image assets are unchanged by this layout update.
- Tablet screen-awake/kiosk settings are **not** configured by this dashboard. Full screen is an explicit browser action; it does not prevent sleep.
- Overview verification: `.venv/bin/python scripts/verify_overview.py` (or `--preview` before publication). Uses `HOMEASSISTANT_URL`/`HOMEASSISTANT_TOKEN`, falling back to the `PI_MCP_` names. The preview config is `build/overview-view.json`, generated with `build_overview_view` from current floor views; preflight overrides only the browser implementation of the existing All floors view. Tests 1280×800, 1024×768, 1024×600, 800×600, 1920×1080, phone fallback, fullscreen, all 13 independent layers, contacts and disconnected states; no physical device operations. Evidence: `build/reports/overview-verification.json` and `build/previews/overview-published-*.png`.
- Exact rollback for this addition: read the current dashboard/hash, remove only the view whose path is `all-floors` through the dashboard patch API, verify the remaining views, then remove resource `29e8596ade0d4b889df1c46fd9b4fa8c` if no other view uses it. Do not restore the whole instance. `build/reports/before-overview.json` records the pre-change dashboard.

The organization cleanup made **no HA writes** and changed **none of the published image bytes, configuration, entity IDs or card JavaScript**. Old hosted images were not purged; only local historical files were removed.

The latest **first-floor design update** places the garden horizontally against the rear wall below the stairs and softly illuminates both the car and front door from the existing circuit. It changes only the first-floor card and three images; floors 2/3, the BMW dimensions/pose, bathroom, mini kitchen and other bindings are preserved. See `floors/first-floor/README.md` and `build/reports/first-floor-update.json`.

The latest third-floor correction centres Corridor Light 2's illumination at the **CORRIDOR** label area and slightly softens Juan's warm Light 2 (100 instead of 120 render watts). Juan's neutral light and Balcony Light 1 remain unchanged. The fourth-floor reference model adds a top-left laundry sink, washer immediately below, aligned descending stairs top-right and a tiled roof at the front. No devices or circuits were added; existing first-/second-floor cards and all their images are preserved.

All 13 lights are independent on/off controls. All off targets only that floor's configured lights. Juan's Light 1 neutral / Light 2 warm are two relay render colours, not HA brightness/colour-temperature capabilities. The separate corridor-named pair is **Light 1 balcony / Light 2 corridor**, using the original IDs. No third-floor bathroom light is mapped. HA's Living Room area belongs to floor 3, not the floor-2 sofa.

Front-door/garage contacts remain **read-only**: Open / Closed / Unavailable; taps open details, never door services. Unknown/missing/disconnected contacts never appear closed. Rendered door poses are static. Floor-2 bathroom-2/3 hotspots hide on compact screens but their controls remain; all five third-floor hotspots stay visible down to 320 px.

## Work on a floor

Dependencies: Blender 5.2.1 LTS (Cycles; OPTIX on this machine), `/usr/bin/chromium`, and the Python environment in `.venv` using `requirements.lock.txt`. Blender needs clean system Python paths; the wrapper handles that. No HA restart, new app or open port is needed.

```bash
cd /home/tamayotchi/Projects/ha-floorplan

# 1. Edit and save floors/third-floor/model.blend in Blender.
# 2. Validate current architectural/material constraints.
./scripts/floorplan models

# 3. Render only the edited floor; omit 3 to render all floors.
./scripts/floorplan render 3
./scripts/floorplan prepare

# 4. Read-only browser preflight and local checks.
# Credentials remain outside the project; never print or commit them.
source ~/.config/pi-secrets/mcp.env
./scripts/floorplan preview
./scripts/floorplan check
```

`render 1,3` selects multiple floors; `render 4` renders only the fourth-floor background. With no selector, all four floors render. Model-only floors need no per-circuit/all-on renders. `project` updates label/hotspot projections without rendering. Current raw renders for unselected floors are retained; `prepare` derives all active images from them. `models --approved` and `check --approved` additionally require exact approved fingerprints/checksums; use these for preservation checks, not to reject intentional future design changes. Refresh the approval record only after reviewing and approving a new state.

### Publish only when a visual/config change is intended

```bash
.venv/bin/python scripts/deploy_assets.py
.venv/bin/python scripts/publish_dashboard_cards.py \
  --preserve-view first-floor --preserve-view second-floor --dry-run
# Review the patch; remove --dry-run only when ready to publish.
./scripts/floorplan verify
./scripts/floorplan check --published
```

Asset deployment uploads changed images, verifies returned bytes and registers the runtime card. The publisher uses the connected **home-assistant MCP** server, a fresh optimistic-lock hash and complete read-back. It never removes views automatically. `--preserve-view` aborts unintended changes; `--allow-add-view` is required for genuinely new views. `--images-only` rejects other card changes.

A real future dashboard patch saves **one overwritten safety record** at `build/reports/before-publish.json`, not a growing revision/backup tree. A dry run creates no snapshot and performs no HA write. Never edit HA `.storage` directly or restore an entire instance to undo this dashboard.

Default browser verification uses mocked device services. **No physical devices are operated.** The optional `verify --live` mode physically toggles/restores one light per device-equipped floor and requires explicit permission; it is not needed for normal development. Contacts are never actuated.

## Checks and privacy

`./scripts/floorplan models --approved` verifies the four standalone files, packed textures, current geometry/materials, full-size BMW clearance, open-stairwell samples, Juan's furniture/window arrangement and fourth-floor sink/washer/descending-stair layout. `./scripts/floorplan check --approved --published` verifies 17 hosted image hashes, the full dashboard, 13 independent light bindings, two contacts, the device-free fourth floor and 20 responsive screenshots, including landscape tablets at 1024×768 and 1024×600. The offline suite has 14 tests, including explicitly authorized view additions, overview asset/binding reuse and model-only binding rejection.

Reorganization also compared every floor's geometry/UVs/materials, camera and lights before/after extraction. Base/all-on test renders matched to within a one-byte channel difference in a tiny number of pixels (GPU rounding); the published PNGs were byte-identical during that organization-only cleanup. Subsequent design updates replace only the affected floor's images. Current evidence is under `build/reports/`.

Keep the whole project folder locally for continued editing. Only the three expressly selected README previews are intended for public sharing; the remainder is private working data. Do not redistribute the embedded BMW as an isolated asset. HA image URLs are reachable without authentication by anyone who knows the URL and can reach the server. No house files were uploaded to external modelling/conversion services.
