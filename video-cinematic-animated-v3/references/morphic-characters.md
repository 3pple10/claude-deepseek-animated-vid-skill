# Morphic Characters

Characters are defined once at story level and referenced by beats via `params.character_id`.
The agent assigns parameters; the renderer draws the result.
No scene hardcodes a character shape.

## Story-level character block

```json
{
  "characters": {
    "hero": {
      "id": "hero",
      "body_type": "average",
      "height_class": "adult_avg",
      "real_height_cm": 170,
      "skin_tone": "medium_light",
      "hair_color": [60, 40, 20],
      "hair_style": "short",
      "eye_type": 2,
      "outfit_class": "trendy",
      "outfit_color_primary": [30, 100, 180],
      "outfit_color_accent": [255, 190, 82],
      "outfit_additive": "hood"
    }
  }
}
```

## Body types

| Value | Shoulder | Hip | Use for |
|---|---|---|---|
| `slim` | 28% of height | 22% | lean adult, teen |
| `average` | 34% | 28% | default adult |
| `sturdy` | 42% | 36% | stocky adult |
| `broad` | 50% | 44% | large adult |

## Height classes and real_height_cm ranges

| Class | Range (cm) | Typical use |
|---|---|---|
| `baby` | 40–65 | infant |
| `toddler` | 66–100 | small child |
| `kid` | 101–140 | child |
| `teen` | 141–164 | teenager |
| `adult_short` | 155–164 | short adult |
| `adult_avg` | 158–178 | average adult |
| `adult_tall` | 179–210 | tall adult |

`real_height_cm` drives world-scale sizing. It must fall within ±5 cm of the class range.

## Skin tones (named palettes)

`pale`, `fair`, `light`, `medium_light`, `medium`, `medium_dark`, `dark`, `deep`, `warm_deep`, `cool_deep`

Or pass a raw `[R, G, B]` list.

## Hair styles

`short`, `long`, `bun`, `cap`, `bald`, `afro`, `fade`

## Eye types (1–6)

| # | Style | Notes |
|---|---|---|
| 1 | Round | Classic Pip default |
| 2 | Almond / narrow | Adult, calm |
| 3 | Wide anime | Expressive, young |
| 4 | Dot | Simple, minimal |
| 5 | Rectangular / visor | Robot, sci-fi |
| 6 | Closed / content | Happy, eyes-shut |

## Outfit classes (content-agnostic, fits any story)

| Class | Description | Allowed additives |
|---|---|---|
| `common` | No outfit, skin only | (none) |
| `normal` | Shirt and trousers | `collar`, `pattern` |
| `trendy` | Hoodie or jacket | `hood`, `stripe`, `logo` |
| `worker` | Vest, boots | `vest`, `apron`, `helmet` |
| `athletic` | Fitted top, track pants | `stripe`, `number` |
| `tactical` | Structured jacket, belt | `collar`, `badge`, `belt` |

Outfit polygon vertices are expressed as fractions of the body's torso anchor points,
so they scale correctly at any world-scale size without any per-character math.

## Drawing from a scene

```python
from engine import character as CH
from engine import world as WO

# Get the character definition from ctx.characters
char = ctx.characters.get("hero", CH.DEFAULT_CHARACTER)

# Get pixel dimensions from world scale
rect = WO.place_on_ground("adult_avg", "center", depth=1.0, aspect_ratio=0.5)

CH.draw_character(
    img, ctx.cam,
    cx         = rect["cx"],
    cy_bottom  = rect["bottom"],
    px_height  = rect["h"],
    char       = char,
    t          = ctx.t,
    mood       = "happy",   # neutral | happy | worried | shock
    look       = (0.2, 0),  # eye direction (dx, dy) in -1..1
)
```
