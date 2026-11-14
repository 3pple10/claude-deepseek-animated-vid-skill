# SVG Asset Library

The agent searches by tag and mood and gets back asset IDs.
It never reads SVG files directly. The renderer loads and composites them.

## Manifest format (assets/svg_library/manifest.json)

One JSON array. One entry per SVG:

```json
{
  "id": "bench_017",
  "tags": ["furniture", "outdoor", "park", "seating", "urban"],
  "category": "Signs of Life",
  "layer": "midground",
  "mood": ["neutral", "calm", "busy"],
  "real_height_cm": 90,
  "aspect_ratio": 1.8,
  "ground_anchor_y": 1.0,
  "file": "assets/svg_library/svgs/bench_017.svg",
  "source": "kenney.nl",
  "license": "CC0",
  "pick_count": 0,
  "last_used": null
}
```

`ground_anchor_y`: fraction of the asset's height where the base touches the ground.
1.0 = bottom edge. 0.5 = mid-point (useful for items like bollards set into ground).

## Five ground-layer categories

Every scene should include at least 2 of these 5 categories in its ground layer.

| Category | Contents |
|---|---|
| `Paved Asphalt` | Roads, sidewalks, intersections, concrete slabs |
| `Natural Ground` | Pebbles, dirt paths, tire ruts, puddles, mud |
| `Living Cover` | Grass, weeds, fallen leaves, moss, roadside bushes |
| `Boundaries` | Walls, fences, gates, concrete dividers, guardrails |
| `Signs of Life` | Streetlights, poles, bins, benches, vehicles, litter |

## Searching from a scene

```python
from engine import assets as AS, tracker as TR

tracker = TR.load()
results = AS.search_svgs(
    tags     = ["outdoor", "urban", "bench"],
    category = "Signs of Life",
    mood     = "neutral",
    top_k    = 6,
    tracker  = tracker,
)
# results is a list of manifest entries, best first
bench_id = results[0]["id"]
```

## Compositing an asset

```python
from engine import assets as AS, world as WO

rect = WO.place_on_ground("park_bench", "right", depth=0.7, aspect_ratio=1.8)
AS.composite_asset(img, bench_id, rect=rect)
```

## Novelty tracker (assets/pick_tracker.json)

Updated automatically after every build. Rules:
- Assets picked in the last build: 95% novelty penalty.
- Assets never picked: 4× novelty bonus.
- Any category representing >30% of all picks: 60% penalty.
- At least 1 of every 4 picks comes from the never-picked pool.

Call `engine.tracker.summary(tracker)` to inspect the state.

## Free CC0 library sources

| Source | URL | Volume | Notes |
|---|---|---|---|
| Kenney Assets | kenney.nl | 50k+ | CC0, game-ready, already layered |
| SVGRepo | svgrepo.com | 500k+ | Mostly MIT/CC0 |
| OpenGameArt | opengameart.org | 10k+ | CC0/CC-BY, environment packs |
| Vecteezy (free) | vecteezy.com | 100k+ | Attribution required |

Start with Kenney. Assets are CC0, stylistically consistent, designed for compositing.

## Auto-tagging a raw library (one-time setup)

`scripts/tag_library.py` renders each SVG as a 256×256 thumbnail and calls
a vision model to generate tags. Run once after adding a batch of SVGs.
Estimated cost at Haiku pricing: ~$8–15 per 100k SVGs.
