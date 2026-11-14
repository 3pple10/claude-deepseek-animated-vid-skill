# Story Formula (procedural track)

Our own structure for 30 to 60 second explainer shorts. The validator enforces the order and required roles.

| Role | Job | Length |
|---|---|---|
| hook | one surprising claim, ends on the payoff word | 10 to 16 words |
| setting | when and where, in one breath | 8 to 14 words |
| escalation | what looked fine; build comfort (repeat once or twice) | 10 to 20 words |
| snap | the moment it goes wrong; give it silence after | 10 to 16 words |
| deadpan | a dry two-part line (good news / bad news) | 12 to 18 words |
| explanation | the mechanism, with one concrete comparison; split across 2 beats | 10 to 22 words each |
| consequence | what happened, said plainly | 10 to 16 words |
| twist | a callback to the hook as a one-line lesson | 8 to 14 words |

## Writing rules
1. One idea per beat, max 28 words, spoken rate about 2.7 words per second.
2. Put the punchline word last in its sentence; cue the visual on that word with `"on": "word"`.
3. Every number or claim gets a `facts` entry with a real source URL. No source, no claim.
4. Use real, checkable events or clearly label fiction (`"factual": false`).
5. Say "most likely" or "presumably" when the sources do.
6. Write the twist so it re-reads the hook.

## Cue timing
Visual cues fire `lead_frames` (default 2) before their word starts, so the picture lands just ahead of the voice. Target words by text, not index: `{"on": "destroyed"}`.

## Picking scenes
Match the beat to a scene from `procedural-engine.md`. Reuse a scene with different params and camera instead of inventing new ones.
