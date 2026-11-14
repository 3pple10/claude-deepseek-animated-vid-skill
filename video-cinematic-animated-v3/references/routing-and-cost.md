# Routing and Cost

Use capability classes, not brand names. The operator maps classes to real providers in `platform/providers.json`.

| Need | Class |
|---|---|
| Keyframes, identity stills | keyframe_image |
| Cheap motion tests | draft_i2v |
| Final faces, product, lip-sync | final_i2v |
| Pure mood or abstract | draft_t2v / final_t2v |
| Native audio in clip | audio addon |

## Economics
1. Plan with the cheap text model (near-zero cost).
2. One keyframe per subject per scene, approved once.
3. Draft-tier i2v for every shot, short.
4. Final tier only on approved shots.
5. Reuse keyframes and refs across shots and projects (Identity Vault).
6. Run `vc.py cost` before any render.

Credits in `providers.json` are relative placeholder units until the operator sets real prices.
