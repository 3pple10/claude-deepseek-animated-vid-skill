#!/usr/bin/env python3
"""vc.py - validate, cost and compile a Shot Graph. Python stdlib only.

  python vc.py validate plan.json [--check-files] [--json]
  python vc.py cost plan.json [--pricing providers.json]
  python vc.py compile plan.json -o jobs.json [--pricing providers.json]

Exit code 1 when validate finds errors. Messages are written as instructions
so a weak planner model can repair the plan in one pass.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRICING = os.path.join(HERE, "..", "platform", "providers.json")

MOVES = ["static", "dolly in", "dolly out", "pull-back reveal", "push-in", "tracking",
         "steadicam", "handheld", "crane up", "crane down", "orbit", "bullet time",
         "crash zoom", "dolly zoom", "whip pan", "pan", "tilt up", "tilt down",
         "rack focus", "fpv"]
FRAMINGS = ["extreme wide", "wide", "medium", "medium close-up", "close-up", "extreme close-up",
            "over-the-shoulder", "pov", "low angle", "high angle", "dutch angle"]
SPEEDS = ["slow", "medium", "fast", "whip"]
LENSES = ["24mm", "35mm", "50mm", "85mm", "135mm", "anamorphic", "macro"]
START_FROM = ["keyframe", "prev_last_frame", "ref", "none"]
TIERS = ["draft", "final"]
ASPECTS = ["9:16", "16:9", "1:1", "4:5"]
DIRECTIONS = ["left", "right"]
KINDS = ["character", "product", "location"]
GENERIC = ["cinematic camera", "epic", "stunning", "beautiful", "amazing"]
NEGATIVE = ("morphing face, identity drift, extra limbs, floating limbs, jitter, rubbery motion, "
            "over-smoothed skin, warped text, watermark, extra people")
MAX_CHAIN = 4


def validate(plan, check_files=False, base_dir="."):
    E, W = [], []
    e, w = E.append, W.append

    for k in ("title", "platform", "identity", "style", "shots"):
        if k not in plan:
            e(f"plan: add required field '{k}'.")
    if E:
        return E, W

    plat = plan["platform"]
    if plat.get("aspect") not in ASPECTS:
        e(f"platform.aspect: set one of {ASPECTS}.")
    if not isinstance(plat.get("max_seconds"), (int, float)):
        e("platform.max_seconds: set a number of seconds.")

    style = plan["style"]
    for k in ("look", "light_dir"):
        if not style.get(k):
            e(f"style.{k}: add a value.")

    ids = {}
    for i, ident in enumerate(plan["identity"]):
        p = f"identity[{i}]"
        if not ident.get("id"):
            e(f"{p}: add 'id'.")
            continue
        if ident["id"] in ids:
            e(f"{p}: id '{ident['id']}' is duplicated; make ids unique.")
        ids[ident["id"]] = ident
        if ident.get("kind") not in KINDS:
            e(f"{p}.kind: set one of {KINDS}.")
        if not ident.get("descriptor"):
            e(f"{p}.descriptor: write one locked descriptor (reused verbatim every shot).")
        if check_files:
            for r in ident.get("ref_images", []):
                if not os.path.exists(os.path.join(base_dir, r)):
                    e(f"{p}.ref_images: file '{r}' not found; fix the path or remove it.")
        if ident.get("kind") in ("character", "product") and ident.get("locked", True) \
                and not ident.get("ref_images"):
            w(f"{p}: '{ident['id']}' has no ref_images; descriptor-only lock is weak. Ask for a reference image.")

    shots = plan["shots"]
    if not shots:
        e("shots: add at least one shot.")
        return E, W

    seen, total, chain_run = set(), 0.0, 0
    for i, s in enumerate(shots):
        sid = s.get("id", f"#{i}")
        p = f"shot {sid}"
        if "id" not in s:
            e(f"shots[{i}]: add 'id'.")
        elif s["id"] in seen:
            e(f"{p}: duplicate id; make shot ids unique.")
        seen.add(s.get("id"))

        d = s.get("duration")
        if not isinstance(d, (int, float)) or d < 1.5 or d > 15:
            e(f"{p}.duration: set seconds between 1.5 and 15 (prefer 2 to 8).")
        else:
            total += d
            if d > 8:
                w(f"{p}: duration {d}s is long; identity drift grows. Split into shots of 8s or less.")

        if s.get("framing") not in FRAMINGS:
            e(f"{p}.framing: use one of {FRAMINGS}.")

        cam = s.get("camera") or {}
        moves = cam.get("moves")
        if not isinstance(moves, list) or not moves:
            e(f"{p}.camera.moves: add 1 to 3 named moves from references/camera-language.md.")
        else:
            if len(moves) > 3:
                e(f"{p}.camera.moves: {len(moves)} moves; keep at most 3.")
            for m in moves:
                if m not in MOVES:
                    e(f"{p}.camera.moves: '{m}' is not a named move; replace with one of {MOVES}.")
        if cam.get("speed") and cam["speed"] not in SPEEDS:
            e(f"{p}.camera.speed: use one of {SPEEDS}.")
        if cam.get("lens") and cam["lens"] not in LENSES:
            e(f"{p}.camera.lens: use one of {LENSES}.")

        for k in ("action", "setting", "light"):
            if not s.get(k):
                e(f"{p}.{k}: add a concrete description.")
        text = " ".join(str(s.get(k, "")) for k in ("action", "mood", "setting", "light")).lower()
        for g in GENERIC:
            if g in text:
                w(f"{p}: generic word '{g}'; replace with a concrete visual.")

        subs = s.get("subject_ids", [])
        for sub in subs:
            if sub not in ids:
                e(f"{p}.subject_ids: '{sub}' is not in identity; add it or fix the id.")
        if subs and not s.get("weight_cue"):
            e(f"{p}.weight_cue: add one cue showing mass or contact (foot plant, cloth lag, contact shadow).")

        sf = s.get("start_from")
        if sf not in START_FROM:
            e(f"{p}.start_from: use one of {START_FROM}.")
        locked_subs = [x for x in subs if x in ids and ids[x].get("kind") in ("character", "product")
                       and ids[x].get("locked", True)]
        if sf == "none" and locked_subs:
            e(f"{p}.start_from: locked subject {locked_subs} cannot use text-to-video. Use 'ref', 'keyframe' or 'prev_last_frame'.")
        if sf == "ref" and not any(ids[x].get("ref_images") for x in subs if x in ids):
            e(f"{p}.start_from: 'ref' needs a subject with ref_images. Add refs or use 'keyframe'.")
        if sf == "prev_last_frame":
            if i == 0:
                e(f"{p}.start_from: first shot has no previous shot; use 'ref' or 'keyframe'.")
            else:
                prev = shots[i - 1]
                if not set(subs) & set(prev.get("subject_ids", [])):
                    w(f"{p}: chains from {prev.get('id')} but shares no subject; use 'keyframe' for a new scene.")
        chain_run = chain_run + 1 if sf == "prev_last_frame" else 0
        if chain_run + 1 > MAX_CHAIN:
            e(f"{p}: chain longer than {MAX_CHAIN} shots. Re-anchor with start_from 'ref' or 'keyframe'.")

        if s.get("tier", "draft") not in TIERS:
            e(f"{p}.tier: use 'draft' or 'final'.")

        if i == 0:
            if s.get("light_dir") and s["light_dir"] != style.get("light_dir") and not s.get("continuity_note"):
                w(f"{p}: light_dir differs from style.light_dir; align it or add continuity_note.")
        else:
            prev = shots[i - 1]
            if s.get("light_dir") and prev.get("light_dir") and s["light_dir"] != prev["light_dir"] \
                    and not s.get("continuity_note"):
                w(f"{p}: light_dir changed from {prev['light_dir']} to {s['light_dir']}; fix it or add continuity_note.")
            a, b = prev.get("screen_direction"), s.get("screen_direction")
            if a in DIRECTIONS and b in DIRECTIONS and a != b and set(subs) & set(prev.get("subject_ids", [])) \
                    and not s.get("axis_note"):
                w(f"{p}: screen direction flips {a} to {b} for the same subject (180 rule). Keep it or add axis_note.")

    if isinstance(plat.get("max_seconds"), (int, float)) and total > plat["max_seconds"]:
        e(f"shots: total {total}s exceeds platform.max_seconds {plat['max_seconds']}. Cut or shorten shots.")
    if plan.get("preset") == "social-reel" and shots[0].get("duration", 0) > 3:
        w("shot 1: reel hook should land in the first 1.5 to 2.5s; shorten shot 1.")
    if plan.get("preset") == "talking-head":
        for s in shots:
            if s.get("duration", 0) > 8:
                w(f"shot {s.get('id')}: talking-head clips over 8s drift in lip-sync; split.")
    return E, W


def load_pricing(path):
    with open(path or DEFAULT_PRICING) as f:
        return json.load(f)


def _kf_key(s):
    return s.get("keyframe_group") or (tuple(sorted(s.get("subject_ids", []))), s.get("setting"), s.get("light_dir"))


def cost(plan, pricing):
    pr = pricing["prices"]
    kf_seen, kf_cost, rows = set(), 0.0, []
    for s in plan["shots"]:
        mode = "t2v" if s["start_from"] == "none" else "i2v"
        d = s["duration"]
        audio = pr.get("audio_addon_per_sec", 0) * d if s.get("audio") == "native" else 0.0
        draft = pr[f"draft_{mode}"] * d + audio
        final = pr[f"final_{mode}"] * d + audio
        if s["start_from"] == "keyframe":
            k = str(_kf_key(s))
            if k not in kf_seen:
                kf_seen.add(k)
                kf_cost += pr["keyframe_image"]
        rows.append({"shot": s["id"], "mode": mode, "draft": round(draft, 3), "final": round(final, 3)})
    draft_total = sum(r["draft"] for r in rows) + kf_cost
    final_total = sum(r["final"] for r in rows) + kf_cost
    as_planned = sum(r[s.get("tier", "draft")] for r, s in zip(rows, plan["shots"])) + kf_cost
    out = {"unit": pricing.get("credits_unit"), "keyframes": round(kf_cost, 3), "per_shot": rows,
           "draft_all": round(draft_total, 3), "final_all": round(final_total, 3),
           "as_planned": round(as_planned, 3),
           "draft_then_final_worst_case": round(draft_total + final_total - kf_cost, 3)}
    mx = (plan.get("budget") or {}).get("max_credits")
    if mx is not None:
        out["budget"] = mx
        out["draft_within_budget"] = draft_total <= mx
        out["worst_case_within_budget"] = out["draft_then_final_worst_case"] <= mx
    return out


def _descriptors(plan, sub_ids):
    m = {i["id"]: i for i in plan["identity"]}
    return "; ".join(m[x]["descriptor"] for x in sub_ids if x in m)


def _motion_prompt(plan, s, anchored):
    cam = s["camera"]
    speed = f" ({cam['speed']})" if cam.get("speed") else ""
    lens = f", {cam['lens']} lens" if cam.get("lens") else ""
    parts = [f"{s['framing']}, {', '.join(cam['moves'])}{speed}{lens}."]
    parts.append(s["action"].rstrip(".") + ".")
    if s.get("weight_cue"):
        parts.append(s["weight_cue"].rstrip(".") + ".")
    parts.append(f"{s['setting']}, {s['light']}.")
    if s.get("mood"):
        parts.append(f"Mood: {s['mood']}.")
    if anchored:
        parts.append("Maintain exact identity, clothing and logo from the start frame.")
    else:
        d = _descriptors(plan, s.get("subject_ids", []))
        if d:
            parts.append(f"Subject: {d}.")
    parts.append(plan["style"]["look"].rstrip(".") + ".")
    return " ".join(parts)


def _keyframe_prompt(plan, s):
    d = _descriptors(plan, s.get("subject_ids", []))
    return (f"Still frame, no motion blur. {plan['style']['look']}. {s['framing']}. "
            f"{('Subject: ' + d + '. ') if d else ''}{s['setting']}, {s['light']}.")


def compile_plan(plan, pricing):
    jobs, kf_steps = [], {}
    shots = plan["shots"]
    refs_of = {i["id"]: i.get("ref_images", []) for i in plan["identity"]}
    max_chars = pricing.get("limits", {}).get("max_prompt_chars", 1200)
    for idx, s in enumerate(shots):
        sid, sf = s["id"], s["start_from"]
        mode = "t2v" if sf == "none" else "i2v"
        tier = s.get("tier", "draft")
        deps, start = [], None
        sub_refs = [r for x in s.get("subject_ids", []) for r in refs_of.get(x, [])]
        if sf == "keyframe":
            k = str(_kf_key(s))
            if k not in kf_steps:
                step_id = f"{sid}.keyframe"
                kf_steps[k] = step_id
                jobs.append({"id": step_id, "type": "keyframe", "class": "keyframe_image",
                             "prompt": _keyframe_prompt(plan, s), "negative": NEGATIVE,
                             "aspect": plan["platform"]["aspect"],
                             "inputs": {"reference_images": sub_refs}, "depends_on": []})
            deps.append(kf_steps[k])
            start = f"keyframe:{kf_steps[k].split('.')[0]}"
        elif sf == "prev_last_frame":
            prev = shots[idx - 1]["id"]
            deps.append(f"{prev}.last_frame")
            start = f"last_frame:{prev}"
        elif sf == "ref":
            start = f"ref:{sub_refs[0]}" if sub_refs else None
        prompt = _motion_prompt(plan, s, anchored=(sf != "none"))
        if len(prompt) > max_chars:
            print(f"warning: {sid} prompt is {len(prompt)} chars (> {max_chars}); shorten action or setting.",
                  file=sys.stderr)
        jobs.append({"id": f"{sid}.animate", "type": "animate", "class": f"{tier}_{mode}",
                     "mode": mode, "tier": tier, "duration": s["duration"],
                     "aspect": plan["platform"]["aspect"], "prompt": prompt, "negative": NEGATIVE,
                     "audio": s.get("audio", "none"),
                     "inputs": {"start_image": start, "reference_images": sub_refs},
                     "depends_on": deps})
        nxt = shots[idx + 1] if idx + 1 < len(shots) else None
        if nxt and nxt["start_from"] == "prev_last_frame":
            jobs.append({"id": f"{sid}.last_frame", "type": "extract_last_frame",
                         "depends_on": [f"{sid}.animate"]})
    return {"title": plan["title"], "aspect": plan["platform"]["aspect"], "jobs": jobs}


def _load(path):
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vc.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("plan"); v.add_argument("--check-files", action="store_true"); v.add_argument("--json", action="store_true")
    c = sub.add_parser("cost"); c.add_argument("plan"); c.add_argument("--pricing")
    k = sub.add_parser("compile"); k.add_argument("plan"); k.add_argument("-o", "--out"); k.add_argument("--pricing")
    a = ap.parse_args(argv)

    plan = _load(a.plan)
    if a.cmd == "validate":
        E, W = validate(plan, a.check_files, os.path.dirname(os.path.abspath(a.plan)))
        if a.json:
            print(json.dumps({"errors": E, "warnings": W}, indent=2))
        else:
            for m in E: print("ERROR  ", m)
            for m in W: print("WARNING", m)
            print(f"{len(E)} error(s), {len(W)} warning(s)")
        return 1 if E else 0
    E, _ = validate(plan)
    if E:
        print("Plan has errors; run validate and fix them first.", file=sys.stderr)
        return 1
    pricing = load_pricing(a.pricing)
    if a.cmd == "cost":
        print(json.dumps(cost(plan, pricing), indent=2)); return 0
    out = compile_plan(plan, pricing)
    txt = json.dumps(out, indent=2)
    if a.out:
        with open(a.out, "w") as f: f.write(txt)
        print(f"wrote {a.out} ({len(out['jobs'])} jobs)")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
