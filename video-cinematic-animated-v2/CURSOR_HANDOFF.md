# Cursor Handoff: video-cinematic (two engines)

Read this first. Do not re-research the design. Build on what exists and verify it. Do not copy any third-party repo (see `RIGHTS.md`).

## Design in one paragraph
Cheap text planners (DeepSeek) cannot render pixels. So plans are strict JSON that scripts validate and repair. Two engines consume them. **Procedural** (`engine/`, our own Python renderer): Story Graph -> voice-timed beats -> keyed cameras -> synthesized sound -> frame QA -> finished short, free per clip and drift-free. **Generative** (`scripts/vc.py`): Shot Graph -> validated, priced, compiled jobs for image-to-video providers. `platform/` wraps both behind one API with draft/final economics, QC gates and credits.

## State at handoff (verified by running code)
| Item | Evidence |
|---|---|
| `python scripts/test_vc.py` | 25 tests pass (shot-graph rules, cost, compile, ffmpeg helpers) |
| `python scripts/test_story.py` | 28 tests pass (story rules, cameras, word alignment, cue lead, determinism, every scene renders, mix loudness, ducking, QA on synthetic bad clips) |
| Demo: `assets/examples/units-story.json` | builds a 59.6 s 1080x1920 short; see `out/work/qa.json` |
| QA found real defects on first build | dead air and cue-window gaps; fixed by adding ambient motion and a windowed frozen metric, then rebuilt |
| SKILL.md | 77 lines (limit 500); frontmatter parses |

## NOT done or NOT verified
1. Voice is `espeak-ng` (robotic placeholder). Need a licensed TTS or real recordings; word timing is estimated and envelope-snapped, not forced-aligned.
2. Only 9 scenes exist. Output quality is "clean cut-paper explainer", not studio animation. No 3D, no lip sync, no character acting beyond 4 moods.
3. Generative engine has no real provider adapters; `providers.json` prices are placeholders; no real generated clip has been rendered.
4. DeepSeek reliability on either schema is unmeasured.
5. Frame cost: about 0.06 to 0.26 s per frame on one CPU core. A 60 s short takes about 4 to 5 minutes. No GPU path.
6. Skill description trigger accuracy not eval-tested.
7. Legal review of the espeak-ng GPL note and any trademark use in stories (see `RIGHTS.md`).

## Tasks in order (each has an acceptance test)
1. Baseline: both test suites pass before any change.
2. **Planner eval harness**: `evals/topics.jsonl` (30 topics). Send SKILL.md + topic to DeepSeek and to a Claude model, run validate/repair, record first-pass valid rate and rounds to valid for both schemas. Targets: DeepSeek first-pass >= 60%, valid after repair >= 95%.
3. **Voice**: integrate a licensed TTS adapter and forced alignment; keep `beats[i].audio` override. Acceptance: cue-to-word error under 3 frames on 20 clips.
4. **Scene library growth**: add 15 scenes (maps, charts, timelines, UI mockups, product spin, people-with-props). Each needs a unit smoke test and a QA pass (no dead air).
5. **Worker + API**: run `story.py build` as a queued job, matching `platform/openapi.yaml` including `engine: auto`. Acceptance: kill worker mid-render, resume without double charge.
6. **Auto engine router**: classify a brief into procedural vs generative; measure agreement with human labels on 40 briefs.
7. **Generative adapters** (see ARCHITECTURE.md): one image, one cheap i2v, one premium i2v; real prices; one real 4-shot draft render.
8. **Style system**: measured style presets (line weight, blur, camera speed ranges) derived from OUR OWN reference renders, never from other creators' frames.
9. **Trigger eval** with the skill-creator loop.

## How to verify (Cursor reports back using this)
Score each 0 to 2 with command output as evidence. 0 missing or broken, 1 partial, 2 works.
- Both suites green on a clean checkout
- `story.py build` on the demo passes its own QA with zero issues
- Planner reliability numbers exist (task 2)
- Rights: no third-party code, frames or audio in the repo (grep, license scan)
- Cost estimate within 15 percent of actual spend (task 7)
- Security list in ARCHITECTURE implemented
Report: score table, failing evidence, change list.

## Guardrails
- Keep SKILL.md lean; new knowledge goes in `references/`.
- Every new rule needs a validator or QA check and a test.
- Never fabricate provider capabilities; cite docs.
- Original assets only; keep `RIGHTS.md` current.
