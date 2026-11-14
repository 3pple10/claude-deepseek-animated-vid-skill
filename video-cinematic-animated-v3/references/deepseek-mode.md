# DeepSeek Mode (weak or cheap planner)

DeepSeek is text-only: it plans, it does not render. Make the plan easy to get right.

1. Output JSON only for the plan, no commentary around it, no markdown fences when piped to a script.
2. Fill the schema in this order: identity, style, shots. Never skip `weight_cue`.
3. Pick moves only from the table in `camera-language.md`. Copy the string exactly.
4. Keep 2 to 5 shots, one action per shot.
5. After `vc.py validate`, read the error list literally and fix only those fields. Do not rewrite the whole plan.
6. Never claim a video was generated. Only claim what a tool returned.
7. Self-check against the Quality Gate in SKILL.md before replying.

Validator messages are written as instructions so a weak model can repair the plan in one pass.

# Premium mode (Claude, Grok, other frontier models)
- Same schema, richer content: 4 to 8 shots, mood arcs, intentional `axis_note` and `continuity_note`.
- Use the model as reviewer: inspect returned frames against refs and score each Quality Gate line.
- Propose alternates for failing shots, then re-validate.
