"""assets.py - SVG asset system for video-cinematic v3.
Loads the manifest, searches assets by tag/mood/category, renders SVGs to
numpy arrays (cached), and composites them onto frames.
The agent never touches SVG files directly — it picks IDs from search results.
"""
from __future__ import annotations
import json, os, hashlib
import numpy as np
import cv2

W, H = 1080, 1920

MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "assets", "svg_library", "manifest.json"
)

# Five world-element ground categories every scene should draw from
GROUND_CATEGORIES = {
    "Paved Asphalt":    "Roads, sidewalks, intersections, concrete slabs",
    "Natural Ground":   "Pebbles, dirt paths, tire ruts, puddles, mud",
    "Living Cover":     "Grass, weeds, fallen leaves, moss, roadside bushes",
    "Boundaries":       "Walls, fences, gates, concrete dividers, guardrails",
    "Signs of Life":    "Streetlights, poles, bins, benches, vehicles, litter",
}

# ------------------------------------------------------------------ manifest
_manifest: list[dict] | None = None
_manifest_index: dict[str, dict] = {}


def _load_manifest() -> list[dict]:
    global _manifest, _manifest_index
    if _manifest is not None:
        return _manifest
    if os.path.exists(MANIFEST_PATH):
        _manifest = json.load(open(MANIFEST_PATH))
    else:
        _manifest = []
    _manifest_index = {a["id"]: a for a in _manifest}
    return _manifest


def get_asset(asset_id: str) -> dict | None:
    _load_manifest()
    return _manifest_index.get(asset_id)


def list_assets(category: str | None = None,
                tags: list[str] | None = None) -> list[dict]:
    m = _load_manifest()
    out = []
    for a in m:
        if category and a.get("category") != category:
            continue
        if tags and not set(tags) & set(a.get("tags", [])):
            continue
        out.append(a)
    return out


# ------------------------------------------------------------------ search
def search_svgs(
    tags:        list[str]  = (),
    category:    str | None = None,
    mood:        str | None = None,
    exclude_ids: list[str]  = (),
    top_k:       int        = 12,
    tracker:     dict | None = None,
) -> list[dict]:
    """
    Search the manifest by tags / category / mood, with novelty scoring.
    Returns up to top_k asset dicts, best-first.
    """
    m = _load_manifest()
    scored = []
    for asset in m:
        if asset["id"] in exclude_ids:
            continue
        if category and asset.get("category") != category:
            continue
        if mood and mood not in asset.get("mood", []):
            # soft filter: allow assets with empty mood list
            if asset.get("mood"):
                continue

        tag_score = len(set(tags) & set(asset.get("tags", [])))
        if tags and tag_score == 0:
            continue

        novelty = 1.0 / (asset.get("pick_count", 0) + 1)
        if tracker:
            if asset["id"] in tracker.get("last_session", []):
                novelty *= 0.05
            if asset["id"] not in tracker.get("pick_counts", {}):
                novelty *= 4.0
            cat_total = sum(tracker.get("category_counts", {}).values()) or 1
            cat_share = tracker.get("category_counts", {}).get(
                asset.get("category", ""), 0) / cat_total
            if cat_share > 0.30:
                novelty *= 0.40

        scored.append((tag_score + novelty * 2, asset))

    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:top_k]]


def pick_assets_for_scene(
    tags:    list[str],
    mood:    str,
    n_picks: int,
    tracker: dict | None = None,
) -> list[dict]:
    """
    Pick n_picks assets. At least 1 comes from the never-picked pool
    (enforces exploration over time).
    """
    normal   = search_svgs(tags=tags, mood=mood, top_k=max(n_picks * 3, 20),
                           tracker=tracker)
    picks    = normal[:max(n_picks - 1, 1)]
    used_ids = {a["id"] for a in picks}

    # Force 1 from never-picked pool if available
    if tracker:
        never = tracker.get("never_picked", [])
        m     = _load_manifest()
        idx   = {a["id"]: a for a in m}
        candidates = [
            idx[nid] for nid in never
            if nid in idx and nid not in used_ids
            and (not mood or not idx[nid].get("mood") or mood in idx[nid]["mood"])
        ]
        if candidates:
            import random
            wild = random.choice(candidates[:max(1, len(candidates) // 5)])
            picks.append(wild)

    return picks[:n_picks]


# ------------------------------------------------------------------ rendering
_svg_cache: dict[tuple, np.ndarray] = {}

def _cairosvg_available() -> bool:
    try:
        import cairosvg
        return True
    except ImportError:
        return False


def render_svg(
    asset_id: str,
    width:    int  = W,
    height:   int  = H,
    tint:     tuple | None = None,
) -> np.ndarray | None:
    """
    Render an SVG asset to a numpy RGBA uint8 array (H x W x 4).
    Returns None if cairosvg is not installed or the file is missing.
    Result is cached by (asset_id, width, height).
    """
    cache_key = (asset_id, width, height)
    if cache_key in _svg_cache:
        base = _svg_cache[cache_key].copy()
    else:
        asset = get_asset(asset_id)
        if asset is None:
            return None
        path = os.path.join(os.path.dirname(__file__), "..", asset["file"])
        if not os.path.exists(path):
            return None
        if not _cairosvg_available():
            return None
        import cairosvg
        png  = cairosvg.svg2png(url=path, output_width=width, output_height=height)
        arr  = np.frombuffer(png, np.uint8)
        rgba = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if rgba is None:
            return None
        if rgba.shape[2] == 3:
            rgba = cv2.cvtColor(rgba, cv2.COLOR_BGR2BGRA)
        # cairosvg returns BGRA; convert to RGBA
        rgba = cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA)
        # Resize to exact (H, W) if needed
        if rgba.shape[:2] != (height, width):
            rgba = cv2.resize(rgba, (width, height), interpolation=cv2.INTER_AREA)
        _svg_cache[cache_key] = rgba.copy()
        base = rgba.copy()

    if tint is not None:
        t = np.array(tint, dtype=np.float32) / 255.0
        base[:, :, :3] = np.clip(
            base[:, :, :3].astype(np.float32) * t, 0, 255
        ).astype(np.uint8)

    return base


def composite_svg(img: np.ndarray, rgba: np.ndarray) -> None:
    """
    Alpha-composite an RGBA layer onto img (RGB, modified in-place).
    img and rgba must be the same spatial dimensions.
    """
    if rgba is None:
        return
    h, w = img.shape[:2]
    rh, rw = rgba.shape[:2]
    if (rh, rw) != (h, w):
        rgba = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    alpha = rgba[:, :, 3:].astype(np.float32) / 255.0
    rgb   = rgba[:, :, :3].astype(np.float32)
    img[:] = np.clip(
        img.astype(np.float32) * (1.0 - alpha) + rgb * alpha, 0, 255
    ).astype(np.uint8)


def composite_asset(
    img:      np.ndarray,
    asset_id: str,
    rect:     dict | None = None,
    tint:     tuple | None = None,
) -> bool:
    """
    Render and composite a named asset onto img.
    If rect is None, the asset fills the whole frame.
    rect keys: x, y, w, h (pixels, floats ok).
    Returns True on success, False if asset unavailable.
    """
    if rect is None:
        rgba = render_svg(asset_id, W, H, tint=tint)
        if rgba is None:
            return False
        composite_svg(img, rgba)
        return True

    rw, rh = max(1, int(rect["w"])), max(1, int(rect["h"]))
    rgba = render_svg(asset_id, rw, rh, tint=tint)
    if rgba is None:
        return False

    x0 = int(rect.get("x", 0))
    y0 = int(rect.get("y", 0))
    x1, y1 = x0 + rw, y0 + rh

    # Clip to frame
    fx0 = max(0, x0);  fy0 = max(0, y0)
    fx1 = min(W, x1);  fy1 = min(H, y1)
    if fx1 <= fx0 or fy1 <= fy0:
        return True   # fully off-screen, not an error

    rx0 = fx0 - x0;   ry0 = fy0 - y0
    rx1 = rx0 + (fx1 - fx0)
    ry1 = ry0 + (fy1 - fy0)

    roi    = img[fy0:fy1, fx0:fx1]
    patch  = rgba[ry0:ry1, rx0:rx1]
    alpha  = patch[:, :, 3:].astype(np.float32) / 255.0
    rgb    = patch[:, :, :3].astype(np.float32)
    img[fy0:fy1, fx0:fx1] = np.clip(
        roi.astype(np.float32) * (1.0 - alpha) + rgb * alpha, 0, 255
    ).astype(np.uint8)
    return True


# ------------------------------------------------------------------ validation
VALID_LICENSES = {"CC0", "CC-BY", "CC-BY-SA", "MIT", "Apache-2.0", "public domain"}

def validate_manifest_entry(entry: dict) -> list[str]:
    errors = []
    for field in ("id", "tags", "category", "file", "real_height_cm"):
        if field not in entry:
            errors.append(f"manifest entry missing '{field}'")
    if "tags" in entry and len(entry["tags"]) < 2:
        errors.append(f"manifest[{entry.get('id')}]: need at least 2 tags")
    if "real_height_cm" in entry:
        h = entry["real_height_cm"]
        if not isinstance(h, (int, float)) or h <= 0:
            errors.append(f"manifest[{entry.get('id')}].real_height_cm must be > 0")
    if "license" in entry and entry["license"] not in VALID_LICENSES:
        errors.append(
            f"manifest[{entry.get('id')}].license '{entry['license']}' "
            f"not in {VALID_LICENSES}"
        )
    return errors
