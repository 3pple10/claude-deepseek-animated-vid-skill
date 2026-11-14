# Rights and Provenance

Goal: every asset in this product is ours to own and ship. This file records where each part came from.

## What is original (written for this project)
| Part | Notes |
|---|---|
| `engine/gfx.py`, `scenes.py`, `story.py`, `voice.py`, `sound.py`, `qa.py` | Original code. Clean-room: written without copying or reading any third-party animation template or skill source code. |
| Characters ("Pips"), planets, spacecraft, rocket, UI cards | Drawn procedurally by our code. No traced or imported art. |
| SFX and music bed | Synthesized by `sound.py` from oscillators and noise. No samples. |
| Story formula, scene library, schema, validator rules | Our own wording and design. |
| Example story "The Unit That Sank a Spacecraft" | Our own script. Facts are public, each with a source URL in the file. |

## Ideas we share with others (methods, not protected expression)
Voice-first timing, keyed camera moves, measured reference matching, frame-level QA. These are general techniques. We implement them our own way.

## What we deliberately did not do
- No copying, forking, or vendoring of another repo's code, templates, or prompts.
- No use of another creator's reference frames, scripts, characters, or style guide.
- No mimicry of a real person's likeness or voice.

## Third-party components used at runtime (not bundled)
| Component | License | Note |
|---|---|---|
| OpenCV, NumPy, SciPy, Pillow | BSD/Apache-style | Python deps |
| ffmpeg | LGPL/GPL build dependent | external tool called as a process |
| Inter font | SIL OFL | free for commercial use; keep the license file if you redistribute the font |
| espeak-ng | GPL v3 | called as an external program for placeholder voice only; not linked or bundled. Confirm with counsel whether voice output has any obligations before commercial use, or replace it with a licensed voice |

## Before commercial release
1. Replace the espeak placeholder with a licensed TTS or a real recording.
2. Keep a source URL for every factual claim (`facts` in each story).
3. Get a lawyer's read on trademark use if a story names real companies or products.
4. Do not publish other creators' footage as references.
