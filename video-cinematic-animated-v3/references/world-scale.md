# World Scale

Every object's screen size derives from one real-world anchor: an average adult at 170 cm = 1400 px tall.
The agent works in human terms (centimetres, depth 0–1, named X positions).
The renderer converts everything to pixels. The agent never specifies a pixel value.

## The anchor

```
ANCHOR_REAL_CM  = 170    # adult human height
ANCHOR_PIXELS   = 1400   # adult fills most of a 1920 px tall frame
GROUND_Y_PX     = 1700   # Y pixel of the ground line
```

## Size formula

```
px_height = (real_cm / 170) × 1400 × depth
```

Selected results at depth 1.0 (foreground):

| Object | Real height (cm) | Pixel height |
|---|---|---|
| baby | 50 | 412 |
| kid | 120 | 988 |
| adult | 170 | 1400 |
| car | 150 | 1235 |
| streetlight | 600 | 4941 (extends off-frame, correct) |
| cat | 30 | 247 |

## Depth layers

Depth 1.0 = foreground, full size. Depth 0.1 = far background, 10% size.
Far objects also shift their ground contact point higher on screen (perspective).

```
ground_y = GROUND_Y_PX − (1.0 − depth) × 350
screen_x = W/2 + x_world × depth   (horizontal parallax)
```

## Named X positions

| Name | World units |
|---|---|
| `far-left` | −430 |
| `left` | −260 |
| `center-left` | −130 |
| `center` | 0 |
| `center-right` | 130 |
| `right` | 260 |
| `far-right` | 430 |

Or use a raw number (−540 to +540).

## Beat world block (what the agent writes)

```json
{
  "world": {
    "depth_layers": [
      {
        "depth": 0.25,
        "assets": [
          {"id": "building_facade_02", "x": "far-left",
           "object_class": "building_floor", "aspect_ratio": 1.4}
        ]
      },
      {
        "depth": 0.65,
        "assets": [
          {"id": "park_bench_017", "x": "right",
           "object_class": "park_bench", "aspect_ratio": 1.8},
          {"id": "trash_bin_003",  "x": "center-right",
           "object_class": "trash_bin", "aspect_ratio": 0.6}
        ]
      },
      {
        "depth": 1.0,
        "assets": [
          {"id": "character_hero", "x": "center",
           "object_class": "adult_avg", "aspect_ratio": 0.5}
        ]
      }
    ],
    "ground_elements": ["asphalt_crack_004", "bench_017"]
  }
}
```

`ground_elements` is the list of SVG IDs to composite as the ground layer,
drawn before depth layers, covering the bottom of the frame.

## Using from a scene

```python
from engine import world as WO
from engine import assets as AS

# Draw world layers (back to front)
placements = WO.resolve_depth_layers(ctx.world.get("depth_layers", []))
for p in placements:
    AS.composite_asset(img, p["id"], rect=p)

# Or place one object manually
rect = WO.place_on_ground("car", "right", depth=0.7, aspect_ratio=2.5)
AS.composite_asset(img, "car_sedan_01", rect=rect)
```

## Object class size table (from assets/world_scale.json)

Add entries there to extend. Built-in entries cover people, animals, furniture,
street objects, vehicles, and vegetation. See assets/world_scale.json for the full list.
