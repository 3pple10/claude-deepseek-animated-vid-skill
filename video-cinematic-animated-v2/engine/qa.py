"""qa.py - automatic frame + audio QA for finished videos. Original code.
checks: black / white / frozen runs, pop frames (unplanned jumps), duration, loudness + true peak."""
import json, re, subprocess
import numpy as np


def video_stats(path, w=135, h=240):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    n = w * h; prev = None; means, diffs = [], []; global _FR; _FR = []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        f = np.frombuffer(b, np.uint8).astype(np.float32)
        _FR.append(f); means.append(float(f.mean()))
        diffs.append(float(np.abs(f - prev).mean()) if prev is not None else 0.0)
        prev = f
    p.stdout.close(); p.wait()
    return np.array(means), np.array(diffs)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", tail); P = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(I.group(1)) if I else None, float(P.group(1)) if P else None)


def runs(mask, min_len):
    out, s = [], None
    for i, m in enumerate(mask):
        if m and s is None: s = i
        if (not m) and s is not None:
            if i - s >= min_len: out.append((s, i - 1))
            s = None
    if s is not None and len(mask) - s >= min_len: out.append((s, len(mask) - 1))
    return out


def run_qa(path, fps=30, allow_frames=(), expect_dur=None, lufs=(-17.0, -11.0), black_ok=()):
    means, diffs = video_stats(path)
    frames = _FR
    rep = {"frames": len(means), "issues": []}
    add = lambda kind, **k: rep["issues"].append({"kind": kind, **k})
    black = [r for r in runs(means < 4, 4) if not any(r[0] <= b <= r[1] for b in black_ok)]
    for r in black: add("black", start=r[0], end=r[1])
    for r in runs(means > 250, 3): add("white", start=r[0], end=r[1])
    win = np.zeros(len(means))
    for i in range(6, len(means)):
        win[i] = float(np.abs(frames[i] - frames[i - 6]).mean())
    for r in runs(win < 0.2, 12): add("frozen", start=r[0], end=r[1])
    med = float(np.median(diffs)) + 1e-6
    allow = set()
    for a in allow_frames: allow.update((int(a) - 1, int(a), int(a) + 1))
    for i in np.where((diffs > max(14.0, 8 * med)))[0]:
        if int(i) not in allow: add("pop", frame=int(i), diff=round(float(diffs[i]), 1))
    if expect_dur is not None:
        d = len(means) / fps
        if abs(d - expect_dur) > 0.5: add("duration", got=round(d, 2), expected=expect_dur)
    I, P = loudness(path)
    rep["lufs"], rep["peak_db"] = I, P
    if I is None: add("no_audio")
    else:
        if not (lufs[0] <= I <= lufs[1]): add("loudness", lufs=I, allowed=list(lufs))
        if P is not None and P > -0.5: add("clipping", peak=P)
    rep["pass"] = not rep["issues"]
    return rep
