"""world.py - World scale system for video-cinematic v3.
Every object's screen size derives from one real-world anchor (adult = 170 cm).
Depth layers give free perspective. The agent works in human terms (cm, depth 0-1,
x in world units) and never touches pixel values.
"""
from __future__ import annotations
import json, math, os

# ------------------------------------------------------------------ constants
ANCHOR_REAL_CM  = 170      # adult human height in cm  = reference
ANCHOR_PIXELS   = 1400     # adult fills most of a 1920 px tall frame
GROUND_Y_PX     = 1700     # Y pixel where ground line sits
W, H            = 1080, 1920

# Named x positions → world units (-540 to +540)
X_NAMES = {
    "far-left":     -430,
    "left":         -260,
    "center-left":  -130,
    "center":          0,
    "center-right":  130,
    "right":         260,
    "far-right":     430,
}

# ------------------------------------------------------------------ size table
# Loaded from assets/world_scale.json if present; built-in table is the fallback.
_BUILTIN_HEIGHTS = {
    # people
    "baby":           50,   "toddler":        85,
    "kid":           120,   "teen":           155,
    "adult_short":   158,   "adult_avg":      170,
    "adult_tall":    190,
    # animals
    "cat":            30,   "dog_small":       40,
    "dog_large":      75,   "horse":          160,
    # furniture
    "chair":          90,   "stool":           65,
    "table_dining":   75,   "table_coffee":    45,
    "desk":           75,   "bed_single":      55,
    "bed_double":     60,   "sofa":            90,
    # architecture
    "door":          210,   "window":         120,
    "building_floor":300,   "building_story": 320,
    # street objects
    "park_bench":     90,   "trash_bin":      110,
    "fire_hydrant":   65,   "streetlight":    600,
    "utility_pole":  900,   "bus_stop_sign":  250,
    # vegetation
    "tree_small":    400,   "tree_medium":    700,
    "tree_large":   1200,   "shrub":          120,
    "flower":         60,
    # vehicles
    "bicycle":       110,   "scooter":        115,
    "motorcycle":    115,   "car":            150,
    "suv":           185,   "van":            210,
    "pickup_truck":  190,   "semi_truck":     400,
    "bus":           310,   "tram":           340,
    # misc props
    "traffic_cone":   75,   "bollard":         90,
    "mailbox":        120,  "fire_escape_step":200,
    "dumpster":       145,  "ladder":         300,
}

_heights: dict[str, float] | None = None


def _load_heights() -> dict[str, float]:
    global _heights
    if _heights is not None:
        return _heights
    path = os.path.join(os.path.dirname(__file__),
                        "..", "assets", "world_scale.json")
    if os.path.exists(path):
        data = json.load(open(path))
        _heights = {**_BUILTIN_HEIGHTS, **data.get("heights_cm", {})}
    else:
        _heights = dict(_BUILTIN_HEIGHTS)
    return _heights


def real_height_cm(object_class: str) -> float:
    """Return canonical real-world height in cm for a named object class."""
    h = _load_heights()
    if object_class not in h:
        raise KeyError(
            f"world_scale: unknown object class '{object_class}'. "
            f"Add it to assets/world_scale.json or use one of: "
            f"{sorted(h)[:20]} …"
        )
    return h[object_class]


# ------------------------------------------------------------------ core maths
def world_height_px(real_cm: float, depth: float = 1.0) -> float:
    """Convert a real-world height (cm) to pixels at a given depth (0-1)."""
    return (real_cm / ANCHOR_REAL_CM) * ANCHOR_PIXELS * max(0.01, depth)


def place_on_ground(
    object_class: str,
    x_world: float | str,
    depth: float = 1.0,
    aspect_ratio: float = 0.6,
    ground_anchor_y: float = 1.0,
    real_cm: float | None = None,
) -> dict:
    """
    Returns pixel rect for an object placed on the ground plane.

    Parameters
    ----------
    object_class    : canonical name from the size table, or any string when real_cm given
    x_world         : world-unit X position (-540 to +540), or a named string
                      ("left", "center", "right", "far-left", "center-right", etc.)
    depth           : 0.1 = far background, 1.0 = foreground
    aspect_ratio    : width / height ratio of this object's bounding box
    ground_anchor_y : fraction of object height where the base sits (1.0 = bottom)
    real_cm         : override the table lookup with an explicit height

    Returns
    -------
    dict with keys: x, y, w, h, bottom, depth, cx (center-x pixel), cy (center-y pixel)
    """
    if isinstance(x_world, str):
        x_world = X_NAMES.get(x_world, 0)

    h_cm   = real_cm if real_cm is not None else real_height_cm(object_class)
    px_h   = world_height_px(h_cm, depth)
    px_w   = px_h * aspect_ratio

    # Far objects sit higher on screen (perspective ground convergence)
    ground_y = GROUND_Y_PX - (1.0 - depth) * 350

    # Horizontal parallax: objects at depth < 1 shift toward centre
    screen_x = W / 2 + x_world * depth

    top_y    = ground_y - px_h * ground_anchor_y
    left_x   = screen_x - px_w / 2

    return {
        "x":      left_x,
        "y":      top_y,
        "w":      px_w,
        "h":      px_h,
        "bottom": ground_y,
        "cx":     screen_x,
        "cy":     top_y + px_h / 2,
        "depth":  depth,
    }


def scale_relative(base_object: str, target_object: str) -> float:
    """
    Returns the size ratio of target relative to base.
    Useful for drawing two objects side-by-side at correct relative scale.
    e.g. scale_relative("adult_avg", "kid") → 0.706
    """
    h = _load_heights()
    return h[target_object] / h[base_object]


# ------------------------------------------------------------------ depth layers
def resolve_depth_layers(layers: list[dict]) -> list[dict]:
    """
    Takes the agent's world.depth_layers list and returns a flat list of
    placement dicts, sorted back-to-front (lowest depth first) for correct
    occlusion ordering.

    Each input entry looks like:
        {
          "depth": 0.6,
          "assets": [
            {"id": "park_bench_017", "x": "right", "object_class": "park_bench"},
            {"id": "trash_bin_003",  "x": "center-right", "object_class": "trash_bin"}
          ]
        }

    Each output entry adds: x, y, w, h, bottom, cx, cy keys from place_on_ground.
    """
    flat = []
    for layer in sorted(layers, key=lambda l: l.get("depth", 1.0)):
        depth = layer.get("depth", 1.0)
        for asset in layer.get("assets", []):
            obj_class = asset.get("object_class", asset.get("id", "adult_avg"))
            rect = place_on_ground(
                object_class  = obj_class,
                x_world       = asset.get("x", "center"),
                depth         = depth,
                aspect_ratio  = asset.get("aspect_ratio", 0.6),
                ground_anchor_y = asset.get("ground_anchor_y", 1.0),
                real_cm       = asset.get("real_cm"),
            )
            flat.append({**asset, **rect})
    return flat


# ------------------------------------------------------------------ validation
def validate_world(world: dict) -> list[str]:
    """Validate a beat's `world` block. Returns list of error strings."""
    errors = []
    layers = world.get("depth_layers", [])
    for i, layer in enumerate(layers):
        d = layer.get("depth")
        if d is None or not (0.05 <= d <= 1.0):
            errors.append(
                f"world.depth_layers[{i}].depth: "
                f"must be 0.05–1.0, got {d!r}"
            )
        for j, asset in enumerate(layer.get("assets", [])):
            if "id" not in asset:
                errors.append(
                    f"world.depth_layers[{i}].assets[{j}]: missing 'id'"
                )
            x = asset.get("x", "center")
            if isinstance(x, str) and x not in X_NAMES:
                errors.append(
                    f"world.depth_layers[{i}].assets[{j}].x: "
                    f"'{x}' not in {list(X_NAMES)}; or use a number"
                )
    ge = world.get("ground_elements", [])
    if not isinstance(ge, list):
        errors.append("world.ground_elements: must be a list of asset IDs")
    return errors
