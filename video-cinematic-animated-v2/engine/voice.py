"""voice.py - voice synthesis (placeholder espeak-ng) + word timing aligned to the audio envelope. Original code."""
import re, subprocess, wave
import numpy as np
from scipy.signal import resample_poly

SR = 44100


def synth(text, path, rate=165, voice="en-us", pitch=45):
    subprocess.check_call(["espeak-ng", "-v", voice, "-s", str(rate), "-p", str(pitch), "-w", path, text])


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        a = np.frombuffer(w.readframes(n), "<i2").astype(np.float32) / 32768
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    if sr != SR:
        a = resample_poly(a, SR, sr).astype(np.float32)
    return a


def write_wav(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())


def trim(a, thr=0.012, pad=0.04):
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    s, e = max(0, idx[0] - int(pad * SR)), min(len(a), idx[-1] + int(pad * SR))
    return a[s:e]


def envelope(a, hop=0.01):
    h = int(hop * SR)
    n = len(a) // h
    e = np.sqrt((a[:n * h].reshape(n, h) ** 2).mean(1))
    k = np.ones(3) / 3
    return np.convolve(e, k, "same"), hop


def word_times(text, a):
    """distribute words across the spoken audio by length weights, then snap boundaries to envelope minima."""
    words = text.split()
    dur = len(a) / SR
    wts = []
    for w in words:
        core = re.sub(r"\W", "", w)
        wt = len(core) + 2.0
        if w.endswith((",", ";", ":")): wt += 3
        if w.endswith((".", "?", "!")): wt += 6
        wts.append(wt)
    cum = np.cumsum([0] + wts) / sum(wts) * dur
    env, hop = envelope(a)
    b = list(cum)
    for i in range(1, len(words)):
        lo, hi = int(max(0, (b[i] - 0.09) / hop)), int(min(len(env) - 1, (b[i] + 0.09) / hop))
        if hi > lo:
            j = lo + int(np.argmin(env[lo:hi + 1]))
            if env[j] < 0.6 * (env[lo:hi + 1].mean() + 1e-9):
                b[i] = j * hop
    b = np.maximum.accumulate(np.array(b))
    return [{"w": w, "t0": float(b[i]), "t1": float(b[i + 1])} for i, w in enumerate(words)]
