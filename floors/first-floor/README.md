# First floor

**Edit `model.blend`** — one self-contained `Floor 1` scene with packed textures, camera and lights. Current house state, not an intermediate build.

- Full-size grey BMW X4 M40i 2020, 114 meshes. Envelope including mirrors: **2.164246 × 4.752 × 1.625292 m**. Never shrink/distort it to disguise collisions.
- Bathroom clear dimensions: **210 cm across × 100 cm deep**; front sliding door; fixtures along the long dimension.
- Open mini kitchen top-left with a 60-cm sink cabinet and **no room door**.
- Timber/dark-steel return stairs top-right. The planted gravel garden is a **horizontal strip against the rear wall beneath the stair turn**, not lengthwise in the middle of the garage. Its 165 objects were moved together without resizing; footprint is 1.66 m across × 0.84 m deep.
- Original facade, entrance, garage and principal walls retained.
- Parked-car mesh checks pass; these are not surveyed garage-entry, parking, door-opening or accessibility guarantees.

| Function | Existing HA entity |
|---|---|
| Shared car/front-door light | `light.first_floor_front_door_light` |
| Mini kitchen light | `switch.first_floor_mini_kitchen_light` |
| Front-door contact — read-only | `binary_sensor.first_floor_front_door_sensor` |
| Garage contact — read-only | `binary_sensor.first_floor_garage_door` |

The existing entrance circuit now softly illuminates **both the car and front door**. Two virtual render emitters (45 W main wash + 8 W weak door fill) share that same entity and one control; these are not extra HA circuits or measured electrical power. The previous exterior-heavy 135 W render is replaced. The mini-kitchen circuit/settings remain unchanged.

No new garage/bathroom/stair/garden circuit was added. Both contacts show Unavailable for invalid states and only open details when tapped.

Reference plan/photo are under `references/`; subsequent user corrections are embodied in the current model above. BMW attribution/licence record: `../../docs/bmw-x4/README.md`. Its geometry and textures are packed into `model.blend`; the original downloads and importer are no longer retained or required.
Lighting/control mapping: `../../config/lighting-map.json`. Render just this floor with `./scripts/floorplan render 1` from the project root.

Current dashboard publication is recorded in `../../config/approved-state.json`. Model/render checks preserve 303 unrelated first-floor objects, BMW pose/size, bathroom, mini kitchen, stairs and facade. That first-floor update preserved floors 2/3 and all 13 of their PNGs; later changes are documented in those floors' notes. Current evidence: `../../build/reports/first-floor-update.json`, `first-floor-lighting.json` and `project-validation.json`. No physical devices were operated.
