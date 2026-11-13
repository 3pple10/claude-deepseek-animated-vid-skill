# Cursor Handoff: video-cinematic

Read this first. Do not re-research the design. Build on what exists and verify it.

## Design in one paragraph
A cheap text-only planner (DeepSeek) cannot render pixels. The skill makes it output a strict Shot Graph (`assets/plan.schema.json`). Deterministic code (`scripts/vc.py`) enforces director rules (identity lock, named camera moves, weight cues, 180 rule, light continuity, chain limits), prices the plan (draft vs final), and compiles an ordered render job DAG. A platform (`platform/`) executes that DAG through swappable provider adapters, with QC gates. Claude/Grok plug in as premium planner and critic with the same schema.

## State at handoff (verified by running code)
| Item | Status |
|---|---|
| `python scripts/test_vc.py` | 25 tests pass (validator, cost, compiler, ffmpeg normalize/stitch/last-frame) |
| `vc.py validate/cost/compile` on `assets/examples/product-ad.plan.json` | 0 errors, 0 warnings, 6 jobs, dependencies resolve |
| SKILL.md frontmatter and `platform/openapi.yaml` | parse as YAML |
| SKILL.md size | 76 lines (limit 500) |

## NOT done or NOT verified (do not assume)
1. No real provider adapters. `platform/providers.json` classes are `UNBOUND`; all prices are placeholder relative credits.
2. No real render has been run, so presence quality (identity drift, motion weight) is untested end to end.
3. Skill description triggering has not been eval-tested.
4. Planner repair loop is specified, not implemented. DeepSeek reliability on the schema is unmeasured.
5. QC thresholds (identity similarity, flicker) are unset; they need tuning on real clips.
6. Provider names, models, limits: unverified. Look them up from current official docs before binding.

## Tasks in order (each has an acceptance test)
1. **Re-run baseline.** `python scripts/test_vc.py` must pass before any change.
2. **Planner eval harness.** Create `evals/briefs.jsonl` (20+ briefs: ads, reels, talking heads, stories, vague, adversarial). Script sends SKILL.md + brief to a planner model, runs the repair loop, records first-pass valid rate and rounds-to-valid. Accept: report for DeepSeek and for a Claude model; target first-pass valid >= 60% and valid after repair >= 95% on DeepSeek, otherwise strengthen `references/deepseek-mode.md` and validator messages.
3. **Provider adapters.** Implement the adapter interface in `platform/ARCHITECTURE.md` for one image provider and one cheap i2v provider, one premium i2v provider. Bind in `providers.json`, replace placeholder prices with real ones (cite doc URLs in a comment). Accept: one real 4-shot product ad rendered at draft tier from the example plan.
4. **Orchestrator.** Execute `jobs.json` DAG with retries, idempotency, ledger reserve/settle/refund. Accept: kill the worker mid-run, resume with no double charge.
5. **QC gate.** ffprobe, black/frozen, last-to-first frame similarity, optional identity embedding. Accept: synthetic bad clips (black, frozen, wrong aspect) are rejected; a good clip passes.
6. **API server** matching `platform/openapi.yaml`. Accept: contract tests generated from the spec pass.
7. **Chaining quality experiment.** Compare drift with last-frame chaining vs ref re-anchoring at chain lengths 2, 3, 4. Adjust `MAX_CHAIN` from data.
8. **Description trigger eval** with the skill-creator loop; 10 should-trigger and 10 should-not queries.

## How to verify this package (Cursor reports back using this)
Score each 0 to 2 (0 missing/broken, 1 partial, 2 works with evidence). Attach command output as evidence.
- Validator catches each rule in SKILL.md "Hard rules" (write a failing plan per rule)
- Compiler output is executable by a real adapter (task 3)
- Planner reliability numbers exist (task 2)
- Identity retention measured on real renders (task 7)
- Cost estimate within 15 percent of actual provider spend (task 3)
- Security items in ARCHITECTURE non-functional list implemented
Report: score table, failing evidence, and a change list. Do not mark anything 2 without command output.

## Guardrails
- Keep SKILL.md lean; put new knowledge in `references/`.
- Do not add generic video content the model already knows.
- Any new rule needs a validator check and a test.
- Do not fabricate provider capabilities; cite docs.
- Require consent confirmation for uploaded real-person likeness and screen briefs for safety before render.
