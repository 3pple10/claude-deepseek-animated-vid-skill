# Identity and Continuity

## Lock ladder (strongest first)
1. Reference image as start frame. Prompt only motion and camera.
2. Keyframe image generated once from refs plus descriptor, approved, then reused as start frame for every shot of that subject.
3. Last-frame chaining: last frame of shot N is the start frame of N+1 (`start_from: prev_last_frame`).
4. Verbatim descriptor in every prompt (weakest; flagged by validator when no refs).

## Descriptor format (write once, never paraphrase)
`[age] [gender], [hair exact], [eyes], [marks], wearing [outfit exact], [signature prop]`

## Chaining rules
- Chain inside a scene. Cut with a fresh keyframe between scenes.
- Chain maximum 4 shots, then re-anchor to the original reference (drift accumulates). Validator enforces.
- Do not chain across a lighting change; re-keyframe instead.

## Continuity rules (validator checks 1 and 2)
1. **Screen direction (180 rule).** If a subject moves left to right, the next shot of that subject keeps the direction, or states `axis_note` explaining the cross.
2. **Light direction.** `light_dir` stays the same across shots, or add `continuity_note`.
3. Wardrobe and props frozen unless the plan says otherwise.
4. Eyeline and camera height stay compatible across cuts.
5. Emotion arc planned per shot (`mood`), no resets.
6. Match on action: end a shot mid-gesture, start the next on the follow-through.

## Presence cues (put one in `weight_cue`)
foot plant and weight shift, cloth lag behind motion, hair reacting to a turn, breath rise, contact shadow, finger pressure on a prop, recoil on impact, micro-expression before the main expression.

## Product lock
Product photo is the start frame. Describe only camera and environment. Add "preserve exact logo and label text" to action. Use macro or 85mm to protect details.
