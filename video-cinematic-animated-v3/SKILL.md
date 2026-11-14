---
name: video-cinematic
description: Directs short-form video with two engines. The procedural engine renders animated explainer and story shorts in code from a validated Story Graph (voice-timed beats, keyed cameras, synthesized sound, frame QA). The generative engine plans high-presence cinematic AI video as a validated Shot Graph (identity locks, named camera moves, physics cues, cost tiers) for image-to-video tools. Works with cheap text-only planners like DeepSeek and gets stronger with Claude or Grok. Use for YouTube Shorts, reels, animated stories, explainers, product ads, talking heads, character scenes, shot lists, camera moves, keyframes, image-to-video, or any request to make a video, short, reel or ad.
---

# Video Cinematic

You are the director and planner. Cheap text models can run this because plans are strict JSON that scripts validate and repair.

Presence = Identity + Physics + Intent. Identity never drifts, motion has weight, every shot serves a beat.

## Step 0: pick the engine

| Request | Engine | Plan format |
|---|---|---|
| Explainer, story, facts, brand or product explainer, data story, "make a short about X" | procedural | Story Graph (`assets/story.schema.json`) |
| Photoreal people or product macro, live-action look, user supplies a face or product photo | generative | Shot Graph (`assets/plan.schema.json`) |
| Existing footage to edit | neither: use `scripts/frames.sh` | none |

If unsure, default to procedural (zero per-clip cost, no identity drift). Say which engine you chose and why in one line.

## Hard rules (both engines)
1. Plan first, as JSON. Never emit a raw one-shot prompt or loose prose plan.
2. Validate before showing anything. Fix every error; justify or fix warnings.
3. Cameras are data or named moves, never "cinematic camera". A camera never sits still.
4. Never claim a video exists unless a tool returned it. No tools means deliver the validated plan and compiled prompts.
5. Facts need sources. Every claim in a factual story has a URL in `facts`.
6. Own the rights. Use original scripts, characters and sound. Never copy another creator's frames, scripts, or style guide. See `RIGHTS.md`.
7. Draft first, final after approval. Report cost before spending.

## Procedural track (Story Graph)
1. Research the topic; collect facts with source URLs.
2. Write beats in the fixed order in `references/story-formula.md` (hook, setting, escalation, snap, deadpan, explanation, consequence, twist). Max 28 words per beat.
3. Pick a scene per beat from `references/procedural-engine.md`. Set a camera per beat (`from`, `to`, `creep`, `kicks`). Target cues by word text: `{"on": "destroyed"}`.
4. `python scripts/story.py validate story.json` and fix errors.
5. Optional stills: `python scripts/story.py preview story.json --beat b3 --t 2 -o still.png`. Look at them.
6. `python scripts/story.py build story.json -o out.mp4`. It renders, mixes, and runs QA. Read the QA report; fix and rebuild only what failed.
7. Deliver the video, `story.json`, `timeline.json`, `qa.json`, and the facts list.

## Generative track (Shot Graph)
1. Intake once: goal, aspect, seconds, identity refs, style, audio, budget.
2. Identity bible: one locked descriptor per character, product, location, plus ref images.
3. Shot Graph: framing, 1 to 3 named camera moves, action, `weight_cue`, light, `start_from` (keyframe, prev_last_frame, ref, none), screen direction, tier.
4. `python scripts/vc.py validate plan.json`, then `cost`, then `compile -o jobs.json`.
5. Render draft tier, inspect against the quality gate, regenerate only the failing dimension (`references/failure-recovery.md`), then final tier for approved shots.
6. Stitch with `scripts/frames.sh`.

Identity-critical subjects (faces, products, logos) start from an image, never pure text-to-video. Chain at most 4 shots, then re-anchor.

## Quality gate (before delivery)
- [ ] validate passes with zero errors
- [ ] hook lands in the first 3 seconds; payoff or twist lands last
- [ ] camera moves visibly and matches the plan
- [ ] visual cues land on or just before their words
- [ ] identity and style consistent across all shots
- [ ] audio clean: loudness around -14 LUFS, no clipping
- [ ] QA report passes (procedural) or frames reviewed against refs (generative)
- [ ] facts sourced; cost within approved budget

## Anti-patterns
- One giant prompt for a whole story
- Facts without sources
- Static camera holds, or generic words like epic, stunning, cinematic
- Rebuilding everything to fix one beat or shot
- Copying another creator's look, frames, or scripts
- Final-tier rendering before draft approval

## Environment routing
- DeepSeek or another cheap planner: read `references/deepseek-mode.md`; use JSON only and repair from validator errors.
- Render tools or MCP present: `references/tool-integration.md`.
- Building the API product: `platform/ARCHITECTURE.md`.
- Cost and tiers: `references/routing-and-cost.md`.

## References (one hop)
- `references/story-formula.md`, `references/procedural-engine.md` (procedural)
- `references/camera-language.md`, `references/identity-and-continuity.md`, `references/presets.md`, `references/failure-recovery.md` (generative)
- `references/routing-and-cost.md`, `references/deepseek-mode.md`, `references/tool-integration.md`
