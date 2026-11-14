"""story.py - Story Graph validator + timeline + camera + render + mix. Original code (procedural track)."""
import json, math, os, subprocess, sys
import numpy as np
import cv2
from . import gfx, scenes, voice, sound, qa, theme as _theme_mod, world as _world_mod
from .gfx import W, H, Cam, ease, clamp, lerp

# ---- formula definitions (addition F) ----
_FORMULAS = {
    "explainer": {
        "roles":    ["hook","setting","escalation","snap","deadpan",
                     "explanation","consequence","twist"],
        "required": ["hook","setting","snap","explanation","consequence","twist"],
        "last":     "twist",
    },
    "product_ad": {
        "roles":    ["hook","benefit","proof","cta"],
        "required": ["hook","benefit","cta"],
        "last":     "cta",
    },
    "tutorial": {
        "roles":    ["hook","setup","step","payoff"],
        "required": ["hook","setup","payoff"],
        "last":     "payoff",
    },
    "character": {
        "roles":    ["hook","introduce","conflict","turn","resolve"],
        "required": ["hook","introduce","resolve"],
        "last":     "resolve",
    },
    "brand": {
        "roles":    ["hook","world","value","invite"],
        "required": ["hook","value","invite"],
        "last":     "invite",
    },
}

ROLES    = _FORMULAS["explainer"]["roles"]
REQUIRED = _FORMULAS["explainer"]["required"]
CAM_KEYS = ("x", "y", "zoom", "roll")


def widx(text, spec):
    """resolve a cue/sfx target to a word index: {"word": 3} or {"on": "destroyed"} (first match, punctuation ignored)."""
    ws = [("".join(ch for ch in w.lower() if ch.isalnum())) for w in text.split()]
    if "word" in spec: return spec["word"] if 0 <= spec["word"] < len(ws) else None
    if "on" in spec:
        k = "".join(ch for ch in str(spec["on"]).lower() if ch.isalnum())
        return ws.index(k) if k in ws else None
    return None


# ----------------------------------------------------------------- validation
def validate_story(s, timing=None):
    E, W_ = [], []
    e, w = E.append, W_.append
    for k in ("title", "beats"):
        if k not in s: e(f"story: add required field '{k}'.")
    if E: return E, W_
    beats = s["beats"]

    # ---- formula (addition F) ----
    formula_name = s.get("formula", "explainer")
    if formula_name not in _FORMULAS:
        e(f"story.formula: '{formula_name}' unknown; use one of {list(_FORMULAS)}")
        formula_name = "explainer"
    fspec    = _FORMULAS[formula_name]
    f_roles  = fspec["roles"]
    f_req    = fspec["required"]
    f_last   = fspec["last"]

    # ---- theme (addition A) ----
    if "theme" in s:
        for err in _theme_mod.validate_theme(s["theme"]):
            e(err)

    # ---- facts ----
    if s.get("factual", True):
        facts = s.get("facts", [])
        if not facts: e("story.facts: add at least one {claim, source} entry, or set factual to false.")
        for i, f in enumerate(facts):
            if not (f.get("claim") and str(f.get("source", "")).startswith("http")):
                e(f"facts[{i}]: give both 'claim' and a source URL starting with http.")

    ids, last_role, roles = set(), -1, []
    total_words = 0
    for i, b in enumerate(beats):
        p = f"beat {b.get('id', '#' + str(i))}"
        if not b.get("id"): e(f"beats[{i}]: add 'id'.")
        elif b["id"] in ids: e(f"{p}: duplicate id.")
        ids.add(b.get("id"))
        r = b.get("role")
        if r not in f_roles: e(f"{p}.role: use one of {f_roles} for formula '{formula_name}'.")
        else:
            ri = f_roles.index(r)
            if ri < last_role: e(f"{p}.role: '{r}' is out of order for formula '{formula_name}'. Order: {f_roles}.")
            last_role = max(last_role, ri); roles.append(r)
        # world block validation (addition D)
        if "world" in b:
            for err in _world_mod.validate_world(b["world"]):
                e(err)
        txt = b.get("text", "")
        nw = len(txt.split()); total_words += nw
        if nw == 0: e(f"{p}.text: write the narration for this beat.")
        if nw > 28: e(f"{p}.text: {nw} words is too long for one beat; split into two beats (max 28).")
        if r == "hook" and nw > 16: w(f"{p}: hook has {nw} words; the hook should land within about 5 seconds (16 words max).")
        if b.get("scene") not in scenes.SCENES: e(f"{p}.scene: '{b.get('scene')}' is unknown; use one of {sorted(scenes.SCENES)}.")
        cam = b.get("cam")
        if not cam: e(f"{p}.cam: add a camera: {{from:{{...}}, to:{{...}}, creep:0.04}}.")
        else:
            for side in ("from", "to"):
                for k in cam.get(side, {}):
                    if k not in CAM_KEYS: e(f"{p}.cam.{side}: unknown key '{k}'; use {CAM_KEYS}.")
            same = all(abs(cam.get("from", {}).get(k, d) - cam.get("to", cam.get("from", {})).get(k, cam.get("from", {}).get(k, d))) < 1e-9 for k, d in (("x", 0), ("y", 0), ("zoom", 1), ("roll", 0)))
            if same and not cam.get("creep"): e(f"{p}.cam: static camera. Add a 'to' pose or a 'creep' of 0.03 to 0.15 (a camera must never sit still).")
            g = cam.get("glide", [0.1, 0.9])
            if not (0 <= g[0] < g[1] <= 1): e(f"{p}.cam.glide: use [start, end] fractions with 0 <= start < end <= 1.")
        nwords = max(nw, 1)
        for cn, c in (b.get("cues") or {}).items():
            if ("word" in c or "on" in c) and widx(txt, c) is None: e(f"{p}.cues.{cn}: target {c} not found in the text; use an existing word via 'on' or a word index 0..{nwords - 1}.")
            if not any(k in c for k in ("word", "on", "t")): e(f"{p}.cues.{cn}: give 'on' (a word from the text), 'word' (index) or 't' (seconds).")
        for j, sf in enumerate(b.get("sfx") or []):
            if sf.get("name") not in sound.SFX: e(f"{p}.sfx[{j}].name: '{sf.get('name')}' is unknown; use one of {sorted(sound.SFX)}.")
            if ("word" in sf or "on" in sf) and widx(txt, sf) is None: e(f"{p}.sfx[{j}]: target {sf.get('on', sf.get('word'))} not found in the text.")
        if timing:
            t = timing[i]
            if t["dur"] > 9: w(f"{p}: lasts {t['dur']:.1f}s; split it so visuals change at least every 9s.")
            wps = nw / max(t["voice"], 0.1)
            if wps > 3.6: w(f"{p}: speaking rate {wps:.1f} words/s is too fast; shorten the text.")
    for r in f_req:
        if r not in roles: e(f"story: missing a '{r}' beat. Required roles for formula '{formula_name}': {f_req}.")
    if beats and beats[0].get("role") != "hook": e("story: first beat must be role 'hook'.")
    if f_last and beats and beats[-1].get("role") != f_last:
        e(f"story: last beat must be role '{f_last}' for formula '{formula_name}'.")
    if total_words < 50 or total_words > 190: w(f"story: {total_words} words; aim for 70 to 150 (roughly 30 to 60 seconds).")
    if timing:
        tot = sum(t["dur"] for t in timing)
        if tot < 25 or tot > 75: w(f"story: total {tot:.0f}s; Shorts work best at 30 to 60s.")
    return E, W_


# ----------------------------------------------------------------- timeline
def prepare(story, workdir, fps=30):
    os.makedirs(workdir, exist_ok=True)
    # resolve theme (addition A) — stored on story so ctx can read it
    story["_theme"] = _theme_mod.resolve(story.get("theme"))
    vcfg = story.get("voice", {})
    lead = story.get("lead_frames", 2) / fps
    t0 = 0.0
    for b in story["beats"]:
        wav = os.path.join(workdir, f"{b['id']}.wav")
        if b.get("audio"): a = voice.read_wav(b["audio"])
        else:
            voice.synth(b["text"], wav, vcfg.get("rate", 165), vcfg.get("voice", "en-us"), vcfg.get("pitch", 45)); a = voice.read_wav(wav)
        a = voice.trim(a); a = a / (np.abs(a).max() + 1e-9) * 0.9
        words = voice.word_times(b["text"], a)
        pre, gap, tail = b.get("pre", 0.2), b.get("gap", 0.35), b.get("tail", 0.0)
        b["_a"], b["_words"], b["_pre"] = a, words, pre
        b["_voice"] = len(a) / voice.SR
        b["_dur"] = max(1.8, pre + b["_voice"] + gap + tail)
        b["_start"] = t0; t0 += b["_dur"]
        cues = {}
        for cn, c in (b.get("cues") or {}).items():
            wi = widx(b["text"], c)
            cues[cn] = (pre + words[wi]["t0"] - lead) if wi is not None else c["t"]
        b["_cues"] = cues
    story["_total"] = t0 + story.get("end_pad", 0.5)
    return story


def timing_of(story):
    return [{"dur": b["_dur"], "voice": b["_voice"]} for b in story["beats"]]


def cam_eval(b, t, d, fps):
    c = b["cam"]; fr, to = c.get("from", {}), c.get("to", c.get("from", {}))
    g = c.get("glide", [0.1, 0.9]); u = ease((t / d - g[0]) / (g[1] - g[0]))
    v = {k: lerp(fr.get(k, dflt), to.get(k, fr.get(k, dflt)), u) for k, dflt in (("x", 0), ("y", 0), ("zoom", 1), ("roll", 0))}
    v["zoom"] *= 1 + c.get("creep", 0.0) * (t / d)
    cam = Cam(v["x"], v["y"], v["zoom"], v["roll"] + c.get("sway", 0.012) * math.sin(t * 1.1))
    for kn in c.get("kicks", []):
        ct = b["_cues"].get(kn)
        if ct is None: continue
        k = int((t - ct) * fps)
        if 0 <= k < 8:
            sgn = -1 if k % 2 else 1; dec = math.exp(-k / 2.6)
            cam.sx += sgn * 26 * dec; cam.sy += -sgn * 15 * dec; cam.roll += sgn * 0.012 * dec
    return cam


def _mood_fn(params):
    moods = params.get("moods", {})
    def f(side, t):
        seq = moods.get("L" if side < 0 else "R", [[0, "neutral"]]); cur = "neutral"
        for t0, m in seq:
            if t >= t0: cur = m
        return cur
    return f


_yy, _xx = np.mgrid[0:H, 0:W]
_VIG = np.clip(1.08 - (np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H / 2) / H) ** 2) * 0.9) ** 2 * 1.25, 0.5, 1.0).astype(np.float32)[..., None]
_WHITE = np.full((H, W, 3), 255, np.uint8)


def post(img, flash):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = cv2.GaussianBlur(np.clip(small.astype(np.int16) - 150, 0, 255).astype(np.uint8), (0, 0), 6)
    out = cv2.add(img, (cv2.resize(br, (W, H)) * 0.7).astype(np.uint8))
    out = (out.astype(np.float32) * _VIG).astype(np.uint8)
    if flash > 0: out = cv2.addWeighted(out, 1 - flash, _WHITE, flash, 0)
    return out


def _draw(story, b, t, fps):
    img = np.zeros((H, W, 3), np.uint8)
    d = b["_dur"]; tt = min(t, d + 0.5)
    cam = cam_eval(b, tt, d, fps)
    ctx = scenes.Ctx(tt, d, fps, cam, b.get("params", {}), b["_cues"], _mood_fn(b.get("params", {})))
    # wire in theme and world (additions A and D)
    ctx.theme = story.get("_theme", {})
    ctx.world = b.get("world", {})
    ctx.characters = story.get("characters", {})
    scenes.SCENES[b["scene"]](img, ctx)
    flash = 0.0
    for cn in b.get("flash", []):
        ct = b["_cues"].get(cn)
        if ct is not None and 0 <= tt - ct < 0.18: flash = max(flash, 0.7 * (1 - (tt - ct) / 0.18))
    return img, flash


def render_frame(story, f, fps=30):
    t = f / fps; beats = story["beats"]
    i = max(j for j, b in enumerate(beats) if b["_start"] <= t + 1e-9)
    b = beats[i]; lt = t - b["_start"]
    img, flash = _draw(story, b, lt, fps)
    xf = 0.0 if b.get("cut") else b.get("xfade", 0.15)
    if i > 0 and xf > 0 and lt < xf:
        pb = beats[i - 1]; pimg, pf = _draw(story, pb, pb["_dur"] + lt, fps)
        k = ease(lt / xf); img = cv2.addWeighted(pimg, 1 - k, img, k, 0)
    return post(img, flash)


# ----------------------------------------------------------------- audio
def build_audio(story, workdir):
    SR = sound.SR; total = story["_total"]
    vt = np.zeros(int(total * SR) + SR, np.float32); sfx = []; levels = []
    for b in story["beats"]:
        s0 = int((b["_start"] + b["_pre"]) * SR); a = b["_a"]; vt[s0:s0 + len(a)] += a[:len(vt) - s0]
        for sf in b.get("sfx") or []:
            wi = widx(b["text"], sf)
            t = b["_start"] + ((b["_pre"] + b["_words"][wi]["t0"] - story.get("lead_frames", 2) / 30) if wi is not None else sf.get("t", 0))
            sfx.append((t, sf["name"], sf.get("gain", 1.0), sf.get("kw", {})))
        lv = b.get("music", 0.6); levels += [(b["_start"], lv), (b["_start"] + b["_dur"] - 0.3, lv)]
    levels = [(0.0, levels[0][1])] + levels + [(total, levels[-1][1])]
    m = sound.music(total, story.get("music", {}).get("mood", "wonder"), story.get("music", {}).get("bpm", 92))
    mono = sound.mix(total, vt, sfx, m, levels)
    raw = os.path.join(workdir, "mix_raw.wav"); fin = os.path.join(workdir, "mix_final.wav")
    sound.write_wav(raw, mono); sound.loudnorm(raw, fin)
    return fin


def allow_frames(story, fps=30):
    """frames where a big visual change is planned: beat boundaries (with crossfade length) and cue effects."""
    out = []
    for i, b in enumerate(story["beats"]):
        if i > 0:
            xf = 0 if b.get("cut") else b.get("xfade", 0.15)
            out += [int(b["_start"] * fps) + k for k in range(-1, int(xf * fps) + 3)]
        for cn, ct in b["_cues"].items():
            out += [int((b["_start"] + ct) * fps) + k for k in range(-2, 13)]
    return out


def build(story_path, out_path, workdir, fps=30, preview_frames=None):
    story = json.load(open(story_path))
    story = prepare(story, workdir, fps)
    E, Wn = validate_story(story, timing_of(story))
    for m in E: print("ERROR  ", m)
    for m in Wn: print("WARNING", m)
    if E: raise SystemExit("story has errors; fix them first")
    audio = build_audio(story, workdir)
    n = int(math.ceil(story["_total"] * fps)) if preview_frames is None else preview_frames
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", audio,
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(render_frame(story, f, fps).tobytes())
        if f % 150 == 0: print(f"frame {f}/{n}", flush=True)
    p.stdin.close(); p.wait()
    tl = {"title": story["title"], "total": story["_total"], "fps": fps, "beats": [{"id": b["id"], "role": b["role"], "start": b["_start"], "dur": b["_dur"], "cues": b["_cues"], "words": b["_words"]} for b in story["beats"]]}
    json.dump(tl, open(os.path.join(workdir, "timeline.json"), "w"), indent=1)
    rep = qa.run_qa(out_path, fps, allow_frames(story, fps), expect_dur=story["_total"])
    json.dump(rep, open(os.path.join(workdir, "qa.json"), "w"), indent=1)
    return story, rep


def preview(story_path, beat_id, t, out_png, workdir, fps=30):
    story = prepare(json.load(open(story_path)), workdir, fps)
    b = next(x for x in story["beats"] if x["id"] == beat_id)
    f = int((b["_start"] + t) * fps)
    cv2.imwrite(out_png, render_frame(story, f, fps)[:, :, ::-1])
