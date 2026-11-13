#!/usr/bin/env python3
"""story.py - procedural story-short pipeline.
  story.py validate story.json
  story.py build story.json -o out.mp4 [--work DIR]
  story.py preview story.json --beat b3 --t 1.2 -o still.png
  story.py qa video.mp4
"""
import argparse, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from engine import story as S, qa


def main(argv=None):
    ap = argparse.ArgumentParser(prog="story.py"); sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("story")
    b = sub.add_parser("build"); b.add_argument("story"); b.add_argument("-o", "--out", required=True); b.add_argument("--work", default=None)
    p = sub.add_parser("preview"); p.add_argument("story"); p.add_argument("--beat", required=True); p.add_argument("--t", type=float, default=1.0); p.add_argument("-o", "--out", required=True); p.add_argument("--work", default=None)
    q = sub.add_parser("qa"); q.add_argument("video")
    a = ap.parse_args(argv)
    work = getattr(a, "work", None) or tempfile.mkdtemp(prefix="story_")
    if a.cmd == "validate":
        st = S.prepare(json.load(open(a.story)), work)
        E, W = S.validate_story(st, S.timing_of(st))
        for m in E: print("ERROR  ", m)
        for m in W: print("WARNING", m)
        print(f"{len(E)} error(s), {len(W)} warning(s); total {st['_total']:.1f}s"); return 1 if E else 0
    if a.cmd == "build":
        _, rep = S.build(a.story, a.out, work); print(json.dumps(rep, indent=1)); return 0 if rep["pass"] else 2
    if a.cmd == "preview":
        S.preview(a.story, a.beat, a.t, a.out, work); print("wrote", a.out); return 0
    rep = qa.run_qa(a.video); print(json.dumps(rep, indent=1)); return 0 if rep["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
