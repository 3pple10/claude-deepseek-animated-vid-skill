# Camera Language

Valid `camera.moves` values (validator enforces this list). Stack at most 3.

| Move | Use for | Prompt fragment |
|---|---|---|
| static | authority, product hero | locked-off tripod, no camera movement |
| dolly in | intimacy, reveal importance | slow dolly in toward the subject |
| dolly out | isolation, context reveal | dolly out revealing the surroundings |
| pull-back reveal | surprise payoff | camera pulls back to reveal |
| push-in | tension | steady push-in |
| tracking | momentum, following | smooth tracking shot beside the subject |
| steadicam | floating walk-and-talk | steadicam follow |
| handheld | urgency, realism | subtle handheld, documentary |
| crane up | scale, closure | crane up rising above the scene |
| crane down | arrival | crane down settling to eye level |
| orbit | hero product, power pose | orbit around the subject at medium distance |
| bullet time | impact beat | bullet-time arc, subject in slow motion |
| crash zoom | shock, punchline | crash zoom into the detail |
| dolly zoom | unease | dolly zoom, background stretches |
| whip pan | transition, energy | whip pan to the next subject |
| pan | scanning | smooth pan left to right |
| tilt up | reveal height | slow tilt up from feet to face |
| tilt down | reveal ground | slow tilt down |
| rack focus | shift attention | rack focus from foreground to subject |
| fpv | speed, immersion | FPV fly-through with banking |

## Framing values
extreme wide, wide, medium, medium close-up, close-up, extreme close-up, over-the-shoulder, pov, low angle, high angle, dutch angle

## Speed values
slow, medium, fast, whip

## Lens values
24mm, 35mm, 50mm, 85mm, 135mm, anamorphic, macro

## Prompt skeleton (what the compiler emits)
`{framing}, {moves} ({speed}), {lens}. {action}. {weight_cue}. {setting}, {light}. {mood}.`

## Pairing guidance
- Hook shots: crash zoom, whip pan, fpv, orbit
- Emotional shots: dolly in, push-in, close-up, 85mm
- Product hero: orbit, static, macro, rack focus
- Payoff: pull-back reveal, crane up
