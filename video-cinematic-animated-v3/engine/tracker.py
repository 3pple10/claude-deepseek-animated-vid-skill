"""tracker.py - Novelty tracker for video-cinematic v3.
Remembers which SVG assets have been picked and how often, so the system
biases toward under-used assets and categories over time.
State lives in assets/pick_tracker.json and is updated after every build.
"""
from __future__ import annotations
import json, os, copy

TRACKER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "assets", "pick_tracker.json"
)

_EMPTY: dict = {
    "pick_counts":      {},   # asset_id -> int
    "category_counts":  {},   # category -> int
    "last_session":     [],   # asset IDs picked in the most recent build
    "never_picked":     [],   # asset IDs with pick_count == 0 (rebuilt on save)
    "total_builds":     0,
}


# ------------------------------------------------------------------ load / save
def load() -> dict:
    if os.path.exists(TRACKER_PATH):
        try:
            data = json.load(open(TRACKER_PATH))
            # backfill missing keys
            for k, v in _EMPTY.items():
                if k not in data:
                    data[k] = copy.deepcopy(v)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return copy.deepcopy(_EMPTY)


def save(tracker: dict) -> None:
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    json.dump(tracker, open(TRACKER_PATH, "w"), indent=2)


# ------------------------------------------------------------------ scoring
def novelty_score(asset: dict, tracker: dict) -> float:
    """
    Returns a novelty score >= 0 for a single asset.
    Higher = more novel = more likely to be picked.

    Rules
    -----
    * Base score = 1 / (pick_count + 1)
    * Last-session penalty: ×0.05  (makes it 95% less likely to repeat)
    * Never-picked bonus:   ×4.0   (strong pull toward unexplored assets)
    * Category fatigue:     ×0.40  (if category > 30% of all-time picks)
    """
    aid = asset["id"]
    base = 1.0 / (tracker["pick_counts"].get(aid, 0) + 1)

    if aid in tracker.get("last_session", []):
        base *= 0.05

    if aid not in tracker.get("pick_counts", {}):
        base *= 4.0

    cat_total = sum(tracker.get("category_counts", {}).values()) or 1
    cat_share = tracker.get("category_counts", {}).get(
        asset.get("category", ""), 0) / cat_total
    if cat_share > 0.30:
        base *= 0.40

    return base


# ------------------------------------------------------------------ update
def record_picks(picked_ids: list[str],
                 manifest: list[dict],
                 tracker: dict) -> dict:
    """
    Update the tracker after a build.
    picked_ids : flat list of all asset IDs used in this build.
    manifest   : the full asset manifest (needed to rebuild never_picked).
    Returns the updated tracker (also mutates it in-place).
    """
    tracker["last_session"] = list(picked_ids)
    tracker["total_builds"] = tracker.get("total_builds", 0) + 1

    manifest_index = {a["id"]: a for a in manifest}

    for aid in picked_ids:
        tracker["pick_counts"][aid] = tracker["pick_counts"].get(aid, 0) + 1
        cat = manifest_index.get(aid, {}).get("category", "")
        if cat:
            tracker["category_counts"][cat] = \
                tracker["category_counts"].get(cat, 0) + 1

    # Rebuild never_picked: all manifest IDs not yet in pick_counts
    tracker["never_picked"] = [
        a["id"] for a in manifest
        if a["id"] not in tracker["pick_counts"]
    ]

    return tracker


# ------------------------------------------------------------------ stats
def summary(tracker: dict) -> dict:
    """Human-readable summary of tracker state."""
    total_picks = sum(tracker["pick_counts"].values())
    top_assets  = sorted(
        tracker["pick_counts"].items(), key=lambda x: -x[1]
    )[:10]
    return {
        "total_builds":      tracker.get("total_builds", 0),
        "total_picks":       total_picks,
        "unique_assets_used": len(tracker["pick_counts"]),
        "never_picked_count": len(tracker.get("never_picked", [])),
        "top_assets":        top_assets,
        "category_counts":   tracker.get("category_counts", {}),
    }


# ------------------------------------------------------------------ reset
def reset(tracker: dict) -> dict:
    """Clear all history. Returns a fresh tracker."""
    return copy.deepcopy(_EMPTY)
