# Second floor

**Edit `model.blend`** — one self-contained `Floor 2` scene. Nominal envelope **5 m wide × 7 m deep**. Rear/top: Lorena left, stairs right; street/front: living area. Connected kitchen/bar left, bathroom right.

- Lorena's two wardrobe bodies/four fronts use **the exact kitchen Cinza grey material**, `V2 · Cinza cabinetry`; not charcoal or oak.
- Bedroom door hinges on the **right entering from the hall**, opening inward toward the right wall. Bathroom door also opens inward; shortened vanity retained.
- Connected sink–stove–breakfast-bar countertop, sofa, vanity, toilet and glazed shower.
- Genuine opening beneath both stair flights/winders, with lower-storey stairs/shaft walls and approach landing. No false floor below the staircase; 255 sample rays validate the opening.
- Kitchen 2 is soft local bar-pendant illumination: two 3 W / 70° render emitters, not a broad living-room light. Render powers are visual parameters, not measured fixture consumption.

| Function | Existing HA entity |
|---|---|
| Kitchen 1 | `light.second_floor_kitchen_light_1` |
| Bar pendants | `light.second_floor_kitchen_light_2` |
| Lorena room | `switch.lorena_room_light` |
| Bathroom 1 | `light.lorena_bathroom_light_1` |
| Bathroom 2 | `light.lorena_bathroom_light_2` |
| Bathroom 3 | `light.lorena_bathroom_light_3` |

HA's Living Room area belongs to floor 3; it is not a substitute circuit for this sofa area. Compact layouts hide only bathroom-2/3 map pins; both explicit controls remain.
References: `references/`. Lighting/control mapping: `../../config/lighting-map.json`. Render just this floor with `./scripts/floorplan render 2` from the project root.
