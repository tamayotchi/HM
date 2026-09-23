# Fourth floor · laundry and roof

`model.blend` is the independent, editable source for this floor: one `Floor 4` scene, packed resources, no linked libraries and no dependency on another floor's file. The provided plan is retained unchanged at `references/floor-plan.png`.

## Layout

- **Laundry sink at the top-left**, with a deep basin, ribbed washboard and tap.
- **Washing machine immediately below the sink**, along the left side, as explicitly requested rather than the drawing's side-by-side appliance arrangement.
- Open laundry area, approximately **4.74 m clear across × 3.21 m deep**, with neutral tiled flooring and white parapets.
- **Stairwell top-right**, aligned to the existing lower floors. The real opening has an approach landing and complete timber/steel stairs descending to floor 3; there is no invented stair flight to a fifth floor.
- The **lower/front part is a sloped tiled roof**, following the roof pattern in the supplied plan.
- Finishes, appliance style, parapets and roof slope are illustrative interpretations—not a construction, structural, waterproofing or accessibility certification.

## Model only—no devices

There are **zero mapped lights, contacts, Zigbee devices or other entities** on this floor. The washing machine is geometry only, not a Home Assistant appliance integration. Ambient daylight is baked into the static background image and does not represent a controllable light.

The dashboard has a **Model only** badge, room labels and no device controls, light counters, All off button or on/off legend. The household still has the same 13 light controls and two read-only contacts on the other floors.

## Edit and render

Open `model.blend` directly. From the project root:

```bash
./scripts/floorplan models
./scripts/floorplan render 4
./scripts/floorplan prepare
```

Only a base image is needed for this floor: `dashboard/images/floor-4-base.png`. A normal render never saves over the model. For dashboard changes, use the shared preflight/publisher workflow in the project README; preserve unaffected views and never create placeholder devices.
