import copy, json, os, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vc

ROOT = os.path.dirname(HERE)
EXAMPLE = os.path.join(ROOT, "assets", "examples", "product-ad.plan.json")
PRICING = vc.load_pricing(None)


def plan():
    with open(EXAMPLE) as f:
        return json.load(f)


def msgs(items, needle):
    return [m for m in items if needle in m]


class Validate(unittest.TestCase):
    def test_example_clean(self):
        E, W = vc.validate(plan())
        self.assertEqual(E, []); self.assertEqual(W, [])

    def test_locked_subject_cannot_t2v(self):
        p = plan(); p["shots"][0]["start_from"] = "none"
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "cannot use text-to-video"))

    def test_unnamed_move_rejected(self):
        p = plan(); p["shots"][1]["camera"]["moves"] = ["cinematic camera"]
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "not a named move"))

    def test_four_moves_rejected(self):
        p = plan(); p["shots"][1]["camera"]["moves"] = ["orbit", "dolly in", "crane up", "pan"]
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "at most 3"))

    def test_missing_weight_cue(self):
        p = plan(); del p["shots"][1]["weight_cue"]
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "weight_cue"))

    def test_light_change_warns(self):
        p = plan(); p["shots"][2]["light_dir"] = "right"
        _, W = vc.validate(p); self.assertTrue(msgs(W, "light_dir changed"))
        p["shots"][2]["continuity_note"] = "scene change to dusk"
        _, W = vc.validate(p); self.assertFalse(msgs(W, "shot s3: light_dir changed"))

    def test_180_rule_warns(self):
        p = plan()
        p["shots"][1]["subject_ids"] = ["runner", "bottle"]
        p["shots"][1]["start_from"] = "ref"
        p["shots"][1]["screen_direction"] = "left"
        _, W = vc.validate(p); self.assertTrue(msgs(W, "180 rule"))
        p["shots"][2]["axis_note"] = "cutaway"
        _, W = vc.validate(p); self.assertFalse(msgs(W, "180 rule"))

    def test_total_duration_overflow(self):
        p = plan(); p["platform"]["max_seconds"] = 10
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "exceeds platform.max_seconds"))

    def test_chain_too_long(self):
        p = plan(); base = p["shots"][1]
        p["platform"]["max_seconds"] = 60
        p["shots"] = [p["shots"][0]] + [dict(copy.deepcopy(base), id=f"c{i}") for i in range(4)]
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "chain longer"))

    def test_first_shot_cannot_chain(self):
        p = plan(); p["shots"][0]["start_from"] = "prev_last_frame"
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "first shot has no previous"))

    def test_unknown_subject(self):
        p = plan(); p["shots"][0]["subject_ids"] = ["ghost"]
        E, _ = vc.validate(p); self.assertTrue(msgs(E, "not in identity"))

    def test_missing_refs_flagged(self):
        p = plan(); p["identity"][0]["ref_images"] = []
        E, W = vc.validate(p)
        self.assertTrue(msgs(W, "descriptor-only lock is weak"))
        self.assertTrue(msgs(E, "'ref' needs a subject with ref_images"))

    def test_reel_hook_warns(self):
        p = plan(); p["preset"] = "social-reel"; p["shots"][0]["duration"] = 5
        _, W = vc.validate(p); self.assertTrue(msgs(W, "reel hook"))

    def test_generic_word_warns(self):
        p = plan(); p["shots"][0]["mood"] = "epic"
        _, W = vc.validate(p); self.assertTrue(msgs(W, "generic word"))

    def test_check_files(self):
        E, _ = vc.validate(plan(), check_files=True, base_dir=tempfile.gettempdir())
        self.assertTrue(msgs(E, "not found"))


class Compile(unittest.TestCase):
    def setUp(self):
        self.out = vc.compile_plan(plan(), PRICING)
        self.jobs = {j["id"]: j for j in self.out["jobs"]}

    def test_dependencies_resolve_and_order(self):
        order = [j["id"] for j in self.out["jobs"]]
        for j in self.out["jobs"]:
            for d in j["depends_on"]:
                self.assertIn(d, self.jobs); self.assertLess(order.index(d), order.index(j["id"]))

    def test_chaining_wired(self):
        self.assertEqual(self.jobs["s2.animate"]["inputs"]["start_image"], "last_frame:s1")
        self.assertIn("s1.last_frame", self.jobs["s2.animate"]["depends_on"])
        self.assertEqual(self.jobs["s4.animate"]["inputs"]["start_image"], "keyframe:s4")

    def test_anchored_prompt_has_no_appearance(self):
        pr = self.jobs["s3.animate"]["prompt"]
        self.assertNotIn("black ponytail", pr); self.assertIn("Maintain exact identity", pr)
        self.assertIn("tracking, push-in", pr)

    def test_keyframe_prompt_has_descriptor(self):
        self.assertIn("matte teal", self.jobs["s4.keyframe"]["prompt"])

    def test_t2v_prompt_has_descriptor_verbatim(self):
        p = plan(); p["identity"][0]["locked"] = False; p["shots"][0]["start_from"] = "none"
        out = {j["id"]: j for j in vc.compile_plan(p, PRICING)["jobs"]}
        self.assertEqual(out["s1.animate"]["class"], "draft_t2v")
        self.assertIn(p["identity"][0]["descriptor"], out["s1.animate"]["prompt"])

    def test_cli_refuses_invalid(self):
        p = plan(); p["shots"][0]["camera"]["moves"] = ["nope"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(p, f)
        self.assertEqual(vc.main(["compile", f.name]), 1)


class Cost(unittest.TestCase):
    def test_draft_cheaper_than_final_and_keyframe_counted(self):
        c = vc.cost(plan(), PRICING)
        self.assertLess(c["draft_all"], c["final_all"]); self.assertEqual(c["keyframes"], 1.0)
        self.assertTrue(c["draft_within_budget"])

    def test_keyframe_dedupe(self):
        p = plan(); s = copy.deepcopy(p["shots"][3]); s["id"] = "s5"
        p["shots"].append(s)
        self.assertEqual(vc.cost(p, PRICING)["keyframes"], 1.0)

    def test_budget_flag(self):
        p = plan(); p["budget"]["max_credits"] = 5
        self.assertFalse(vc.cost(p, PRICING)["draft_within_budget"])


@unittest.skipUnless(subprocess.call(["which", "ffmpeg"], stdout=subprocess.DEVNULL) == 0, "no ffmpeg")
class Frames(unittest.TestCase):
    def test_pipeline(self):
        sh = os.path.join(HERE, "frames.sh"); d = tempfile.mkdtemp()
        a, b = os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")
        for f, src in ((a, "testsrc"), (b, "smptebars")):
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size=320x240:rate=24:duration=1", "-pix_fmt", "yuv420p", f])
        na, nb, out = (os.path.join(d, x) for x in ("na.mp4", "nb.mp4", "out.mp4"))
        subprocess.check_call([sh, "normalize", a, na, "270", "480", "24"])
        subprocess.check_call([sh, "normalize", b, nb, "270", "480", "24"])
        subprocess.check_call([sh, "stitch", out, na, nb])
        last = os.path.join(d, "last.png"); subprocess.check_call([sh, "last-frame", out, last])
        self.assertGreater(os.path.getsize(last), 1000)
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]))
        self.assertAlmostEqual(dur, 2.0, delta=0.3)
        info = subprocess.check_output([sh, "probe", out]).decode()
        self.assertIn("width=270", info); self.assertIn("codec_type=audio", info)


if __name__ == "__main__":
    unittest.main(verbosity=1)
