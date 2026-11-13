# Procedural Engine (our own, in `engine/`)

Renders animated shorts directly in code. No generator, no per-clip cost, no identity drift. Pure Python (OpenCV, NumPy, Pillow, SciPy) plus ffmpeg. Needs no GPU or browser.

## Pipeline
`story.json` -> validate -> voice per beat (word times aligned to the audio) -> timeline -> render frames -> mix (voice, SFX, music, ducking, loudness) -> mux -> QA.

CLI: `python scripts/story.py validate|build|preview|qa`.

## Scene library
| Scene | Use | Params and cues |
|---|---|---|
| hook_counter | big number + object, breaks on cue | `value`, `label`; cue `hit` |
| launch | liftoff with date sticker | `month`, `year`, `liftoff` |
| space_cruise | long journey between two planets | `tag` |
| mission_control | two characters, a note passing between them | `tiny`, `moods` {L,R: [[t, mood]]}; moods neutral, happy, worried, shock |
| mars_approach | spiral toward a planet, planned vs actual path | cue `loss` |
| verdict | two stacked result cards | cues `good`, `bad` |
| units_compare | two arrows, 1x vs 4.45x | cues `a`, `b`, `ratio` |
| burnup | breakup and fireball | none |
| twist_stamp | number, question, unit stamp | cues `q`, `stamp` |

Add a scene: write `@scene("name") def fn(img, ctx)` in `engine/scenes.py`. Use `ctx.t` (seconds in beat), `ctx.d`, `ctx.cam` (project with `cam.p(x, y, depth)`), `ctx.since("cue")` (seconds since a cue, None if undefined), `ctx.p` (params). Keep it deterministic (seeded RNG), draw into `img` (RGB uint8).

## Camera (keyed data, never a prompt)
`cam: {from:{x,y,zoom,roll}, to:{...}, glide:[0.1,0.9], creep:0.04, kicks:["cue"]}`. Glide is a smootherstep between poses. Creep is a constant slow push-in. Kicks are short decaying shakes on cues. A static camera is a validation error.

## Sound
All audio is synthesized by `engine/sound.py` (SFX: whoosh, impact, ding, tick, rumble, static, stamp, blip, sizzle, dropout, riser; generative music bed). Music ducks under the voice. Final mix is normalized to -14 LUFS, true peak under -1.5 dB.

## Voice
Default provider is `espeak-ng` (placeholder, robotic). Replace with a real recording per beat: set `beats[i].audio` to a wav path. Word timing is estimated by length weights then snapped to the audio envelope. Swap in forced alignment later without changing the rest.

## QA (automatic)
black, white and frozen runs; unplanned pop frames; duration; loudness; clipping. Cues, kicks and hard cuts are whitelisted.

## When to use this vs the generative track
| Need | Track |
|---|---|
| Explainers, stories, brand or product explainers, data stories | procedural |
| Anything that must stay identical every frame, zero per-clip cost | procedural |
| Photoreal people, product macro shots, live-action look | generative (Shot Graph) |
