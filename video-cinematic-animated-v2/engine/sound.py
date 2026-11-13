"""sound.py - original synthesized SFX + generative music + voice-ducked mix. No samples, no third-party audio."""
import math, subprocess, wave
import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
_rng = np.random.default_rng(21)


def _t(d): return np.arange(int(d * SR)) / SR
def noise(d): return _rng.standard_normal(int(d * SR)).astype(np.float32)
def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], "band"); return lfilter(b, a, x)
def lp(x, f, order=2):
    b, a = butter(order, f / (SR / 2), "low"); return lfilter(b, a, x)
def env_ar(n, att, rel):
    e = np.ones(n); a, r = int(att * SR), int(rel * SR)
    e[:a] = np.linspace(0, 1, max(a, 1)); e[-r:] = np.minimum(e[-r:], np.linspace(1, 0, max(r, 1))); return e


def whoosh(d=0.6): n = noise(d); return bp(n, 300, 5000) * env_ar(len(n), d * 0.55, d * 0.45) * 2.2
def impact(d=1.0):
    t = _t(d); k = np.sin(2 * np.pi * (140 * np.exp(-t * 18) + 38) * t) * np.exp(-t * 6)
    return k * 1.4 + lp(noise(d), 900) * np.exp(-t * 7) * 0.9
def ding(f=880, d=1.4):
    t = _t(d); return (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3) + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 6)) * np.exp(-t * 3.2) * 0.5
def tick(d=0.04): t = _t(d); return (noise(d) * np.exp(-t * 160) + np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 200) * 0.5) * 0.5
def rumble(d=3.0): n = noise(d); return lp(n, 160) * env_ar(len(n), d * 0.5, d * 0.3) * 4 + lp(noise(d), 1500) * env_ar(len(n), d * 0.6, d * 0.3) * 0.5
def static(d=0.6): n = noise(d); gate = (np.sin(_t(d) * 60) > -0.2).astype(float); return bp(n, 1000, 9000) * gate * env_ar(len(n), 0.02, d * 0.5) * 0.7
def stamp(d=0.9): t = _t(d); return impact(d) * 1.2 + tick(d) * 0.0 + bp(noise(d), 2000, 7000) * np.exp(-t * 40) * 0.8
def blip(f=660, d=0.14): t = _t(d); return np.sign(np.sin(2 * np.pi * f * t)) * 0.18 * env_ar(len(t), 0.005, 0.1)
def sizzle(d=2.0): n = noise(d); return bp(n, 2500, 9000) * env_ar(len(n), d * 0.2, d * 0.6) * 1.1
def dropout(d=1.2): t = _t(d); return np.sin(2 * np.pi * (500 * np.exp(-t * 2.4) + 40) * t) * np.exp(-t * 2.5) * 0.9
def riser(d=1.5): t = _t(d); f = 200 + 1800 * (t / d) ** 2; return np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) * 0.4 + bp(noise(d), 800, 6000) * (t / d) * 0.4

SFX = {"whoosh": whoosh, "impact": impact, "ding": ding, "tick": tick, "rumble": rumble, "static": static,
       "stamp": stamp, "blip": blip, "sizzle": sizzle, "dropout": dropout, "riser": riser}


def music(total, mood="wonder", bpm=92):
    """soft generative bed: pad chords + pulse + sub. Original, rule-based."""
    n = int(total * SR); out = np.zeros(n, np.float32)
    prog = {"wonder": [(57, 'm'), (53, 'M'), (48, 'M'), (55, 'M')], "tense": [(57, 'm'), (56, 'm'), (53, 'M'), (52, 'M')]}[mood]
    bar = 4 * 60 / bpm
    for i in range(int(total / bar) + 1):
        root, q = prog[i % len(prog)]
        ch = [root, root + (3 if q == 'm' else 4), root + 7, root + 12]
        t0 = int(i * bar * SR); d = min(bar + 0.6, total - i * bar)
        if d <= 0: break
        t = _t(d)
        pad = sum(np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * t) * 0.5 + np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * 1.003 * t) * 0.3 for m in ch) * 0.07
        sub = np.sin(2 * np.pi * 440 * 2 ** ((root - 33 - 69) / 12) * t) * 0.18
        pad = (pad + sub) * env_ar(len(t), 0.8, 0.8)
        out[t0:t0 + len(pad)] += pad[:n - t0].astype(np.float32)
        for b in range(4):
            tb = int((i * bar + b * 60 / bpm) * SR)
            tt = _t(0.25); m = ch[(b * 2) % 4] + 12
            pl = np.sin(2 * np.pi * 440 * 2 ** ((m - 69) / 12) * tt) * np.exp(-tt * 9) * 0.06
            if tb + len(pl) <= n: out[tb:tb + len(pl)] += pl
    return out


def mix(total, voice_track, sfx_events, music_track, music_levels):
    """voice_track/music_track arrays at SR; sfx_events [(time, name, gain, kwargs)]; music_levels [(t, level)]."""
    n = int(total * SR)
    v = np.zeros(n, np.float32); v[:min(n, len(voice_track))] = voice_track[:n]
    m = np.zeros(n, np.float32); m[:min(n, len(music_track))] = music_track[:n]
    ts = np.array([p[0] for p in music_levels]); lv = np.array([p[1] for p in music_levels])
    m *= np.interp(np.arange(n) / SR, ts, lv).astype(np.float32)
    h = int(0.05 * SR); k = n // h
    env = np.sqrt((v[:k * h].reshape(k, h) ** 2).mean(1)); env = np.convolve(env, np.ones(6) / 6, "same")
    duck = 1 - 0.7 * np.clip(env / (env.max() * 0.35 + 1e-9), 0, 1)
    duck = np.interp(np.arange(n), (np.arange(k) + 0.5) * h, duck)
    duck = np.convolve(duck, np.ones(int(0.12 * SR)) / int(0.12 * SR), "same").astype(np.float32)
    s = np.zeros(n, np.float32)
    for t0, name, gain, kw in sfx_events:
        x = (SFX[name](**kw) * gain).astype(np.float32); i = int(t0 * SR)
        if 0 <= i < n: s[i:i + len(x)] += x[:n - i]
    mono = v * 1.0 + m * duck * 0.55 + s * 0.6
    return np.tanh(mono * 1.1).astype(np.float32)


def write_wav(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())


def loudnorm(src, dst, I=-14.0, TP=-1.5):
    """two-pass EBU R128 normalisation with ffmpeg."""
    import json, re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    j = json.loads(re.search(r"\{[^{}]*\}", r.stderr[r.stderr.rfind("Parsed_loudnorm"):] if "Parsed_loudnorm" in r.stderr else r.stderr[r.stderr.rfind("{"):], re.S).group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "44100", "-ac", "2", dst])
