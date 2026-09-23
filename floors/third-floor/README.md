# Third floor

**Edit `model.blend`** — one self-contained `Floor 3` scene with the approved current furniture/window/light mapping. Rear/top is away from the street; balcony/street/front is bottom.

- Alejandro rear/top-left beside the stairs; Juan beside the front balcony.
- Juan: **bed bottom-left; black desk and wheeled office chair bottom-right**. The bed headboard clears the facade; existing 35° inward/ajar door is clear of bed/desk/chair in this static pose.
- **Left window section: opaque white wall. Right section: glazed.** Original sill and right-side framing retained.
- Both rooms have wheeled office chairs and **two oak sliding wardrobe leaves** matching their doors. Lorena's floor-2 wardrobes remain kitchen grey.
- Shared approved stairwell/lower stairs and bathroom geometry. Three opaque white balcony half-walls, not glass railings; separate corridor access.
- Geometry remains an illustrative model, not surveyed construction or a door-swing/accessibility guarantee.

| Function | Existing HA entity |
|---|---|
| Alejandro | `switch.alejandro_room_light` |
| Juan Light 1 — neutral | `switch.juan_room_light_1` |
| Juan Light 2 — warm | `switch.juan_room_light_2` |
| **Balcony — Light 1** | `switch.third_floor_corridor_light_1` |
| **Corridor — Light 2** | `switch.third_floor_corridor_light_2` |

The two Light 1/2 pairs are different devices. Do not reverse balcony/corridor or reinterpret Juan's neutral/warm assignment. Preserve legacy entity IDs/order. No sixth circuit or bathroom light is mapped. Colours/powers are render parameters; all controls remain on/off only. All five map pins remain visible at 320 px.

## Current lighting placement and intensity

- **Corridor Light 2** illuminates the corridor at the existing **CORRIDOR** label, plan `(3.55, 3.65)`, rather than the former position farther back by the stairs. Emitter height remains 2.42 and render power 65. The existing map hotspot stays offset for compact-screen touch clearance; it is not an exact fixture-location marker.
- **Juan Light 2 warm** uses 100 render watts, down from 120 for a modest reduction. The measured mean positive light delta in its previously lit area decreased about 7.2%; the warm colour and fixture position are unchanged.
- Juan Light 1 neutral remains 120 render watts; Alejandro and Balcony Light 1 remain unchanged. These numbers describe the image renderer, not measured electricity, physical dimming commands or new HA capabilities.
- All geometry/materials, the camera, ambient illumination and 474 objects other than the moved saved corridor lamp were verified unchanged. Only the warm/corridor layer PNGs were replaced; the base, neutral, Alejandro and balcony PNG bytes are unchanged.

Evidence: `../../build/reports/third-floor-lighting.json`. No physical devices were operated.

References: `references/`. Lighting/control mapping: `../../config/lighting-map.json`. Render just this floor with `./scripts/floorplan render 3` from the project root.
