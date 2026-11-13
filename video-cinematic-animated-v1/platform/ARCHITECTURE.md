# Platform Architecture: Director-First Video API

A new-brand design, not a clone of any existing wrapper. Existing wrappers expose "prompt in, clip out". This platform exposes **a plan as a first-class object** that is validated, priced, approved, then rendered. That is where presence and margin come from.

## Principles
1. Plan before pixels. Every render traces back to an approved Shot Graph.
2. Draft cheap, finalize selectively. Credits are only spent on final tier after approval.
3. Identity is an asset. Reference images and approved keyframes live in an Identity Vault and are reused across shots and projects.
4. The planner is swappable (DeepSeek default, Claude premium). Renderers are swappable behind adapters.
5. Every shot is QC-gated automatically before the user sees it.

## Components
```
Client/API --> Gateway (auth, idempotency, rate limit, credits)
                 |
                 v
            Planner Service  --(LLM: DeepSeek | Claude | other)--> Shot Graph
                 |                         ^ repair loop uses vc.py validate errors
                 v
            Validator/Costing (scripts/vc.py core, port to service)
                 |
                 v
            Orchestrator (job DAG from vc.py compile)
              |-- Keyframe stage --> image adapter
              |-- Animate stage  --> video adapters (draft_i2v, final_i2v, t2v)
              |-- Extract stage  --> ffmpeg worker (last frame chaining)
              |-- QC gate        --> ffprobe + continuity + identity checks
              |-- Assembler      --> ffmpeg normalize + stitch + audio
                 |
            Object storage + Identity Vault + Ledger (credits) + Webhooks
```

## Planner repair loop (makes cheap models reliable)
1. LLM emits Shot Graph JSON (system prompt = SKILL.md + references on demand).
2. Run validate. If errors: send the error list back verbatim, ask for a corrected JSON. Max 3 rounds.
3. If still failing: fall back to preset template from `references/presets.md` filled with the brief.
4. Premium tier: add a critic pass (frontier model reviews plan for narrative, continuity, hook).

## Job state machine (per shot)
`planned -> keyframe_pending -> keyframe_ready -> draft_rendering -> qc -> draft_ready -> (approved) -> final_rendering -> qc -> final_ready`
Failure edges: `qc_failed -> auto_retry (max 2, failing dimension only) -> simplified_retry -> needs_user`.
Project states: `planning -> awaiting_plan_approval -> rendering_drafts -> awaiting_shot_approval -> rendering_finals -> assembling -> done`.

## QC gate (automated, cheap, runs on every clip)
| Check | Method | Fail action |
|---|---|---|
| Valid media | ffprobe: duration, resolution, fps, streams | retry |
| Frozen or black output | frame difference and mean luma sampling | retry |
| Chain continuity | image similarity between last frame of N and first frame of N+1 | re-anchor to ref |
| Identity drift | face or object embedding similarity vs ref at 3 sample frames (optional model, configurable threshold) | retry with shorter clip |
| Aspect and duration | compare to plan | reject |
| Flicker | luminance variance across frames | lower motion, retry |
Thresholds are config, tuned on real renders (not set in this repo).

## Economics
- Planning cost near zero (cheap LLM). Charge a plan fee or bundle it.
- Draft tier gives users a cheap preview; final tier carries the margin.
- Keyframe reuse: cache by (identity ids, setting, light) key (matches `keyframe_group`).
- Bring-your-own-provider-keys mode for power users; managed credits for everyone else.
- Credits ledger is append-only; reserve on submit, settle on completion, refund on provider failure.

## Adapter interface (implement per provider)
```
submit(job) -> provider_job_id
poll(provider_job_id) -> {status, output_url?, error?}
cancel(provider_job_id)
capabilities() -> {class, max_seconds, aspects, supports_start_image, supports_audio}
estimate(job) -> credits
```
Bind classes in `providers.json` to adapters. All prices there are placeholders until verified against real providers.

## Non-functional requirements
Idempotency keys on every POST; webhook signing (HMAC) with retries; per-user storage isolation; signed URLs; provider timeouts and circuit breakers; structured logs per job id; content-safety screening on briefs and refs before render; consent record for any uploaded person's likeness.
