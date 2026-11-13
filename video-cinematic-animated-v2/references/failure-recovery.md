# Failure Recovery

Fix only the failing dimension. Never restart the plan.

| Symptom | Likely cause | Fix |
|---|---|---|
| Face morphs mid-shot | long clip, weak lock | shorten to 4 s, i2v from ref, exact-identity line |
| Face differs shot to shot | chain too long | re-anchor to original ref, new keyframe |
| Outfit changes | descriptor paraphrased | paste descriptor verbatim, add ref image |
| Logo or text warps | low res, fast move | macro or 85mm, slower camera, preserve exact logo |
| Floaty motion | no weight cue | add foot plant, cloth lag, contact; lower motion strength |
| Rubber limbs | too much action per clip | one action per shot, shorter |
| Camera ignored | move vague or stacked | one named move plus speed |
| Jitter or flicker | high motion strength | lower strength, static or steadicam |
| Extra people | open scene description | "single subject only", narrow setting |
| Lighting jumps | light_dir changed | fix light_dir, re-keyframe |
| Lip-sync off | clip too long | split per sentence, under 8 s |
| Cost blowing up | final tier too early | return to draft, lock approved shots |

Retry budget: 2 regenerations per shot, then simplify the shot (fewer moves, closer framing, shorter) instead of retrying the same prompt.
