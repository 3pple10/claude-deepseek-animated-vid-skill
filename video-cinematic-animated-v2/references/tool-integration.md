# Tool Integration

Detect what exists, then choose a mode. Never fabricate a tool.

| Environment | Mode |
|---|---|
| No render tools | compile prompts, user pastes into a generator |
| Image gen tool only | generate keyframes, deliver animate prompts |
| Video gen tool or MCP | run `jobs.json` steps in order, draft first |
| Platform API (`platform/openapi.yaml`) | POST plan, poll job, review frames, approve final |
| ffmpeg shell | `scripts/frames.sh` for last-frame, stitch, probe |

## Job step contract (from `vc.py compile`)
Each shot yields steps: `keyframe` (optional), `animate`, `extract_last_frame`. Steps carry `depends_on`. Execute in dependency order. Replace `inputs.start_image` references (`keyframe:s1`, `last_frame:s2`, `ref:<path>`) with real paths or URLs returned by earlier steps.

## After every render
1. `scripts/frames.sh probe clip.mp4`
2. Extract first, mid, last frames and compare to refs
3. Score the Quality Gate; store the result with the shot
