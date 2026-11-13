import copy, json, math, os, subprocess, sys, tempfile, unittest
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from engine import story as S, scenes, voice, sound, qa, gfx

EX = os.path.join(ROOT, "assets", "examples", "units-story.json")
WORK = tempfile.mkdtemp(prefix="tst_")
def raw():
    with open(EX) as f: return json.load(f)
HAS_ESPEAK = subprocess.call(["which", "espeak-ng"], stdout=subprocess.DEVNULL) == 0
def has(msgs, needle): return any(needle in m for m in msgs)


class Validate(unittest.TestCase):
    def test_example_clean(self):
        E, W = S.validate_story(raw()); self.assertEqual(E, [], E); self.assertEqual(W, [], W)
    def test_missing_role(self):
        s = raw(); s["beats"] = [b for b in s["beats"] if b["role"] != "snap"]
        E, _ = S.validate_story(s); self.assertTrue(has(E, "missing a 'snap'"))
    def test_out_of_order(self):
        s = raw(); s["beats"][4], s["beats"][5] = s["beats"][5], s["beats"][4]
        E, _ = S.validate_story(s); self.assertTrue(has(E, "out of order"))
    def test_static_camera(self):
        s = raw(); s["beats"][2]["cam"] = {"from": {"zoom": 1.0}, "to": {"zoom": 1.0}}
        E, _ = S.validate_story(s); self.assertTrue(has(E, "static camera"))
        s["beats"][2]["cam"]["creep"] = 0.05
        E, _ = S.validate_story(s); self.assertFalse(has(E, "static camera"))
    def test_unknown_scene_and_sfx(self):
        s = raw(); s["beats"][0]["scene"] = "nope"; s["beats"][0]["sfx"] = [{"name": "boom", "t": 0}]
        E, _ = S.validate_story(s); self.assertTrue(has(E, "unknown")); self.assertTrue(has(E, "sfx[0].name"))
    def test_long_text(self):
        s = raw(); s["beats"][2]["text"] = " ".join(["word"] * 30)
        E, _ = S.validate_story(s); self.assertTrue(has(E, "too long for one beat"))
    def test_sources_required(self):
        s = raw(); s["facts"] = []
        E, _ = S.validate_story(s); self.assertTrue(has(E, "story.facts"))
        s["factual"] = False; E, _ = S.validate_story(s); self.assertFalse(has(E, "story.facts"))
        s = raw(); s["facts"][0]["source"] = "nope"; E, _ = S.validate_story(s); self.assertTrue(has(E, "source URL"))
    def test_bad_cue_target(self):
        s = raw(); s["beats"][0]["cues"]["hit"] = {"on": "banana"}
        E, _ = S.validate_story(s); self.assertTrue(has(E, "not found in the text"))
    def test_first_last_roles(self):
        s = raw(); s["beats"][0]["role"] = "setting"
        E, _ = S.validate_story(s); self.assertTrue(has(E, "first beat must be role 'hook'"))
    def test_widx(self):
        t = "The orbiter goes silent."
        self.assertEqual(S.widx(t, {"on": "Silent"}), 3); self.assertEqual(S.widx(t, {"word": 1}), 1)
        self.assertIsNone(S.widx(t, {"on": "mars"})); self.assertIsNone(S.widx(t, {"word": 9}))


class Camera(unittest.TestCase):
    def beat(self, **cam):
        return {"cam": cam, "_cues": {"hit": 1.0}}
    def test_endpoints_and_creep(self):
        b = self.beat(**{"from": {"x": -100, "zoom": 1.0}, "to": {"x": 100, "zoom": 2.0}, "glide": [0, 1]})
        c0, c1 = S.cam_eval(b, 0, 4, 30), S.cam_eval(b, 4, 4, 30)
        self.assertAlmostEqual(c0.x, -100); self.assertAlmostEqual(c1.x, 100); self.assertAlmostEqual(c1.zoom, 2.0)
        b = self.beat(**{"from": {"zoom": 1.0}, "creep": 0.1}); self.assertGreater(S.cam_eval(b, 3, 4, 30).zoom, S.cam_eval(b, 0, 4, 30).zoom)
    def test_smooth_midpoint(self):
        b = self.beat(**{"from": {"x": 0}, "to": {"x": 100}, "glide": [0, 1]}); self.assertAlmostEqual(S.cam_eval(b, 2, 4, 30).x, 50, places=3)
    def test_kick_window(self):
        b = self.beat(**{"from": {"zoom": 1}, "creep": 0.01, "kicks": ["hit"]})
        self.assertNotEqual(S.cam_eval(b, 1.0 + 1 / 30, 4, 30).sx, 0)
        self.assertEqual(S.cam_eval(b, 1.5, 4, 30).sx, 0); self.assertEqual(S.cam_eval(b, 0.5, 4, 30).sx, 0)


class VoiceAlign(unittest.TestCase):
    def test_snaps_to_gaps(self):
        sr = voice.SR; burst = lambda: np.sin(2 * np.pi * 220 * np.arange(int(0.5 * sr)) / sr).astype(np.float32) * 0.5
        gap = np.zeros(int(0.12 * sr), np.float32)
        a = np.concatenate([burst(), gap, burst(), gap, burst()])
        wt = voice.word_times("aa bb cc", a)
        self.assertEqual(len(wt), 3)
        self.assertTrue(all(wt[i]["t1"] <= wt[i + 1]["t0"] + 1e-6 for i in range(2)))
        g1, g2 = 0.5, 1.12
        self.assertTrue(g1 - 0.02 <= wt[1]["t0"] <= g1 + 0.14); self.assertTrue(g2 - 0.02 <= wt[2]["t0"] <= g2 + 0.14)
        self.assertAlmostEqual(wt[-1]["t1"], len(a) / sr, places=2)
    def test_monotonic_synth(self):
        if not HAS_ESPEAK: self.skipTest("no espeak")
        p = os.path.join(WORK, "v.wav"); txt = "One pound of force is about four and a half newtons."
        voice.synth(txt, p); a = voice.trim(voice.read_wav(p)); wt = voice.word_times(txt, a)
        self.assertEqual(len(wt), len(txt.split()))
        for x, y in zip(wt, wt[1:]): self.assertLessEqual(x["t0"], y["t0"])
        self.assertTrue(2 < len(a) / voice.SR < 6)


@unittest.skipUnless(HAS_ESPEAK, "no espeak")
class Timeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.st = S.prepare(raw(), WORK)
    def test_cue_lead(self):
        b = self.st["beats"][0]; w = b["_words"][S.widx(b["text"], {"on": "destroyed"})]
        self.assertAlmostEqual(b["_cues"]["hit"], b["_pre"] + w["t0"] - 2 / 30, places=6)
    def test_beats_contiguous(self):
        bs = self.st["beats"]
        for a, b in zip(bs, bs[1:]): self.assertAlmostEqual(a["_start"] + a["_dur"], b["_start"], places=6)
        self.assertGreater(self.st["_total"], 25)
    def test_validate_with_timing_clean(self):
        E, W = S.validate_story(self.st, S.timing_of(self.st)); self.assertEqual(E, []); self.assertEqual(W, [])
    def test_frames_deterministic(self):
        f = int(8 * 30); a, b = S.render_frame(self.st, f), S.render_frame(self.st, f)
        self.assertTrue(np.array_equal(a, b)); self.assertEqual(a.shape, (1920, 1080, 3))
    def test_every_scene_renders(self):
        for name, fn in scenes.SCENES.items():
            for t in (0.0, 1.0, 3.0):
                img = np.zeros((1920, 1080, 3), np.uint8); fn(img, scenes.Ctx(t, 5, 30, gfx.Cam(), {}, {}))
                self.assertGreater(img.std(), 1.0, name)
    def test_audio_mix_levels(self):
        fin = S.build_audio(self.st, WORK)
        I, P = qa.loudness(fin); self.assertTrue(-15.5 <= I <= -12.5, I); self.assertLess(P, -1.0)


class Sound(unittest.TestCase):
    def test_ducking(self):
        sr = sound.SR; n = 4 * sr
        voice_t = np.zeros(n, np.float32); voice_t[sr:2 * sr] = np.sin(2 * np.pi * 180 * np.arange(sr) / sr) * 0.5
        m = np.sin(2 * np.pi * 300 * np.arange(n) / sr).astype(np.float32) * 0.3
        out = sound.mix(4.0, voice_t, [], m, [(0, 1.0), (4, 1.0)])
        under, free = out[int(1.3 * sr):int(1.7 * sr)], out[int(3.0 * sr):int(3.4 * sr)]
        # music-only energy while voice speaks must be lower than when voice is silent
        v_only = voice_t[int(1.3 * sr):int(1.7 * sr)]
        music_under = np.sqrt(np.mean((under - v_only) ** 2)); music_free = np.sqrt(np.mean(free ** 2))
        self.assertLess(music_under, music_free * 0.7)
    def test_sfx_events_placed(self):
        out = sound.mix(3.0, np.zeros(1, np.float32), [(1.0, "impact", 1.0, {})], np.zeros(1, np.float32), [(0, 0), (3, 0)])
        sr = sound.SR; self.assertLess(np.abs(out[:int(0.95 * sr)]).max(), 1e-6); self.assertGreater(np.abs(out[int(1.0 * sr):int(1.2 * sr)]).max(), 0.1)


def lavfi(path, vf_src, dur, audio=True, extra=()):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{vf_src}:size=270x480:rate=30:duration={dur}"] if "=" not in vf_src.split("size")[0] else None
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", vf_src]
    if audio: args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}", "-af", "loudnorm=I=-14:TP=-1.5"]
    subprocess.check_call(args + list(extra) + ["-pix_fmt", "yuv420p", "-t", str(dur), path])


class QA(unittest.TestCase):
    def kinds(self, rep): return {i["kind"] for i in rep["issues"]}
    def test_black_flagged(self):
        p = os.path.join(WORK, "black.mp4"); lavfi(p, "color=c=black:size=270x480:rate=30:duration=3", 3)
        self.assertIn("black", self.kinds(qa.run_qa(p)))
    def test_frozen_flagged(self):
        p = os.path.join(WORK, "frozen.mp4"); lavfi(p, "color=c=0x336699:size=270x480:rate=30:duration=3", 3)
        self.assertIn("frozen", self.kinds(qa.run_qa(p)))
    def test_pop_flagged_and_allowed(self):
        p = os.path.join(WORK, "pop.mp4")
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=270x480:rate=30:duration=3", "-vf",
                               "drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:enable='eq(n,45)'", "-pix_fmt", "yuv420p", p])
        self.assertIn("pop", self.kinds(qa.run_qa(p)))
        self.assertNotIn("pop", self.kinds(qa.run_qa(p, allow_frames=[45])))
    def test_no_audio_and_loudness(self):
        p = os.path.join(WORK, "silent.mp4"); lavfi(p, "testsrc2=size=270x480:rate=30:duration=3", 3, audio=False)
        self.assertIn("no_audio", self.kinds(qa.run_qa(p)))
        loud = os.path.join(WORK, "loud.mp4")
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=270x480:rate=30:duration=3", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                               "-af", "volume=0dB,loudnorm=I=-6:TP=-0.1", "-pix_fmt", "yuv420p", "-t", "3", loud])
        self.assertIn("loudness", self.kinds(qa.run_qa(loud)))
    def test_good_clip_passes(self):
        p = os.path.join(WORK, "good.mp4"); lavfi(p, "testsrc2=size=270x480:rate=30:duration=3", 3)
        rep = qa.run_qa(p); self.assertEqual(rep["issues"], [], rep)


if __name__ == "__main__":
    unittest.main(verbosity=1)
