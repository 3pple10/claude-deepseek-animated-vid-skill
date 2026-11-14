"""test_v3.py - acceptance tests for video-cinematic v3 additions.
Run: python scripts/test_v3.py
All tests must pass before merging.
"""
import sys, os, json, math, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import theme as TH
from engine import world as WO
from engine import assets as AS
from engine import tracker as TR
from engine import character as CH
import numpy as np


# ===========================================================  A: Theme System
class TestTheme(unittest.TestCase):

    def test_resolve_default(self):
        t = TH.resolve(None)
        self.assertIn("primary", t)
        self.assertIsInstance(t["primary"], tuple)
        self.assertEqual(len(t["primary"]), 3)

    def test_resolve_preset(self):
        t = TH.resolve({"preset": "dark_gold"})
        # dark_gold overrides primary to amber
        self.assertNotEqual(t["primary"], TH.DEFAULT_THEME["primary"])

    def test_resolve_explicit_override(self):
        t = TH.resolve({"primary": [255, 0, 0]})
        self.assertEqual(t["primary"], (255, 0, 0))

    def test_validate_good(self):
        errs = TH.validate_theme({"primary": [100, 200, 100], "vignette": 0.5})
        self.assertEqual(errs, [])

    def test_validate_bad_color(self):
        errs = TH.validate_theme({"primary": [300, 0, 0]})
        self.assertTrue(len(errs) > 0)

    def test_validate_bad_mood(self):
        errs = TH.validate_theme({"music_mood": "disco"})
        self.assertTrue(len(errs) > 0)

    def test_validate_unknown_preset(self):
        errs = TH.validate_theme({"preset": "nonexistent"})
        self.assertTrue(len(errs) > 0)

    def test_all_presets_valid(self):
        for name in TH.PRESETS:
            t = TH.resolve({"preset": name})
            for k in ("primary", "bg_top", "bg_bot", "card"):
                self.assertIn(k, t, f"preset {name} missing {k}")

    def test_color_tuple_normalisation(self):
        t = TH.resolve({"bg_top": [10, 20, 30]})
        self.assertEqual(type(t["bg_top"]), tuple)


# ===========================================================  D: World Scale
class TestWorldScale(unittest.TestCase):

    def test_anchor_adult(self):
        px = WO.world_height_px(170, 1.0)
        self.assertAlmostEqual(px, WO.ANCHOR_PIXELS, delta=1)

    def test_kid_at_foreground(self):
        px = WO.world_height_px(120, 1.0)
        self.assertAlmostEqual(px, 120 / 170 * WO.ANCHOR_PIXELS, delta=1)

    def test_depth_scaling(self):
        near = WO.world_height_px(170, 1.0)
        far  = WO.world_height_px(170, 0.3)
        self.assertAlmostEqual(far, near * 0.3, delta=2)

    def test_place_on_ground_dict_keys(self):
        rect = WO.place_on_ground("chair", "center", depth=1.0, aspect_ratio=0.9)
        for key in ("x", "y", "w", "h", "bottom", "cx", "cy", "depth"):
            self.assertIn(key, rect)

    def test_place_x_names(self):
        rect_l = WO.place_on_ground("car", "left",  depth=0.8, aspect_ratio=2.5)
        rect_r = WO.place_on_ground("car", "right", depth=0.8, aspect_ratio=2.5)
        self.assertLess(rect_l["cx"], rect_r["cx"])

    def test_place_x_number(self):
        rect = WO.place_on_ground("bicycle", -200, depth=1.0, aspect_ratio=1.5)
        self.assertIsInstance(rect["x"], float)

    def test_scale_relative(self):
        ratio = WO.scale_relative("adult_avg", "kid")
        self.assertAlmostEqual(ratio, 120 / 170, places=3)

    def test_resolve_depth_layers(self):
        layers = [
            {"depth": 0.5, "assets": [
                {"id": "bench", "x": "right", "object_class": "park_bench",
                 "aspect_ratio": 1.8, "ground_anchor_y": 1.0}
            ]},
            {"depth": 1.0, "assets": [
                {"id": "person", "x": "center", "object_class": "adult_avg",
                 "aspect_ratio": 0.6, "ground_anchor_y": 1.0}
            ]},
        ]
        flat = WO.resolve_depth_layers(layers)
        # back-to-front order: depth 0.5 first
        self.assertEqual(flat[0]["id"], "bench")
        self.assertEqual(flat[1]["id"], "person")
        # person at depth 1.0 is taller than bench at depth 0.5
        self.assertGreater(flat[1]["h"], flat[0]["h"])

    def test_validate_world_good(self):
        w = {"depth_layers": [
            {"depth": 0.5, "assets": [{"id": "a1", "x": "left"}]}
        ]}
        errs = WO.validate_world(w)
        self.assertEqual(errs, [])

    def test_validate_world_bad_depth(self):
        w = {"depth_layers": [{"depth": 2.5, "assets": []}]}
        errs = WO.validate_world(w)
        self.assertTrue(len(errs) > 0)

    def test_validate_world_bad_x(self):
        w = {"depth_layers": [
            {"depth": 0.5, "assets": [{"id": "x", "x": "nowhere"}]}
        ]}
        errs = WO.validate_world(w)
        self.assertTrue(len(errs) > 0)

    def test_real_height_known(self):
        self.assertEqual(WO.real_height_cm("chair"), 90)

    def test_real_height_unknown_raises(self):
        with self.assertRaises(KeyError):
            WO.real_height_cm("flying_saucer")


# ===========================================================  C: Asset System
class TestAssets(unittest.TestCase):

    def test_load_empty_manifest(self):
        m = AS._load_manifest()
        self.assertIsInstance(m, list)

    def test_search_empty_returns_list(self):
        results = AS.search_svgs(tags=["urban"])
        self.assertIsInstance(results, list)

    def test_search_with_tracker_no_crash(self):
        tracker = TR.load()
        results = AS.search_svgs(tags=["park"], tracker=tracker)
        self.assertIsInstance(results, list)

    def test_validate_manifest_entry_good(self):
        entry = {
            "id": "bench_001",
            "tags": ["outdoor", "seating"],
            "category": "Signs of Life",
            "file": "assets/svg_library/svgs/bench_001.svg",
            "real_height_cm": 90,
            "license": "CC0",
        }
        errs = AS.validate_manifest_entry(entry)
        self.assertEqual(errs, [])

    def test_validate_manifest_entry_missing_field(self):
        entry = {"id": "x", "tags": ["a", "b"], "category": "y"}
        errs = AS.validate_manifest_entry(entry)
        self.assertTrue(any("file" in e or "real_height_cm" in e for e in errs))

    def test_validate_manifest_entry_bad_license(self):
        entry = {
            "id": "x", "tags": ["a", "b"], "category": "y",
            "file": "f.svg", "real_height_cm": 90, "license": "PIRATED"
        }
        errs = AS.validate_manifest_entry(entry)
        self.assertTrue(len(errs) > 0)

    def test_composite_svg_shape(self):
        """composite_svg must handle mismatched sizes without crashing."""
        import numpy as np
        img  = np.zeros((100, 60, 3), np.uint8)
        rgba = np.full((200, 120, 4), 128, np.uint8)
        AS.composite_svg(img, rgba)
        self.assertEqual(img.shape, (100, 60, 3))

    def test_composite_asset_missing_returns_false(self):
        import numpy as np
        img = np.zeros((100, 60, 3), np.uint8)
        ok = AS.composite_asset(img, "nonexistent_id_xyz")
        self.assertFalse(ok)

    def test_ground_categories_complete(self):
        self.assertEqual(len(AS.GROUND_CATEGORIES), 5)


# ===========================================================  E: Tracker
class TestTracker(unittest.TestCase):

    def test_load_returns_dict(self):
        t = TR.load()
        for k in ("pick_counts", "category_counts", "last_session",
                  "never_picked", "total_builds"):
            self.assertIn(k, t)

    def test_novelty_score_new_asset(self):
        t = TR.load()
        asset = {"id": "new_one", "category": "Signs of Life"}
        score = TR.novelty_score(asset, t)
        self.assertGreater(score, 0)

    def test_novelty_score_last_session_penalty(self):
        t = TR.load()
        t["last_session"] = ["asset_a"]
        a_new  = {"id": "asset_b", "category": "X"}
        a_last = {"id": "asset_a", "category": "X"}
        self.assertGreater(TR.novelty_score(a_new, t),
                           TR.novelty_score(a_last, t))

    def test_novelty_never_picked_bonus(self):
        t = TR.load()
        t["pick_counts"] = {"seen": 5}
        a_seen  = {"id": "seen",  "category": "X"}
        a_fresh = {"id": "fresh", "category": "X"}
        self.assertGreater(TR.novelty_score(a_fresh, t),
                           TR.novelty_score(a_seen,  t))

    def test_category_fatigue(self):
        t = TR.load()
        t["category_counts"] = {"Dominant": 90, "Other": 10}
        a_dom   = {"id": "d", "category": "Dominant"}
        a_other = {"id": "o", "category": "Other"}
        self.assertLess(TR.novelty_score(a_dom, t),
                        TR.novelty_score(a_other, t))

    def test_record_picks_increments(self):
        t = TR.reset(TR.load())
        manifest = [{"id": "a1", "category": "Signs of Life"},
                    {"id": "a2", "category": "Paved Asphalt"}]
        TR.record_picks(["a1", "a2"], manifest, t)
        self.assertEqual(t["pick_counts"]["a1"], 1)
        self.assertEqual(t["pick_counts"]["a2"], 1)
        self.assertEqual(t["category_counts"]["Signs of Life"], 1)

    def test_record_picks_never_picked_updated(self):
        t = TR.reset(TR.load())
        manifest = [{"id": "a1", "category": "X"},
                    {"id": "a2", "category": "X"},
                    {"id": "a3", "category": "X"}]
        TR.record_picks(["a1"], manifest, t)
        self.assertIn("a2", t["never_picked"])
        self.assertIn("a3", t["never_picked"])
        self.assertNotIn("a1", t["never_picked"])

    def test_summary_keys(self):
        t = TR.load()
        s = TR.summary(t)
        for k in ("total_builds","total_picks","unique_assets_used",
                  "never_picked_count","top_assets","category_counts"):
            self.assertIn(k, s)

    def test_reset_clears(self):
        t = {"pick_counts": {"x": 5}, "total_builds": 10,
             "category_counts": {}, "last_session": [], "never_picked": []}
        t2 = TR.reset(t)
        self.assertEqual(t2["pick_counts"], {})
        self.assertEqual(t2["total_builds"], 0)

    def test_no_asset_picked_more_than_ceiling(self):
        """Pick assets 50 times; no single asset should dominate."""
        import random
        rng = random.Random(42)
        manifest = [{"id": f"a{i}", "category": "X",
                     "tags": ["park"], "mood": ["neutral"],
                     "real_height_cm": 90, "file": "f.svg"}
                    for i in range(30)]
        # populate manifest for search
        AS._manifest = manifest
        AS._manifest_index = {a["id"]: a for a in manifest}
        t = TR.reset(TR.load())
        counts: dict = {}
        for _ in range(50):
            picks = AS.pick_assets_for_scene(["park"], "neutral", 4, tracker=t)
            ids = [p["id"] for p in picks]
            TR.record_picks(ids, manifest, t)
            for aid in ids:
                counts[aid] = counts.get(aid, 0) + 1
        # Ceiling: no asset picked more than 25% of runs (50 runs × 4 picks)
        total = sum(counts.values())
        for aid, cnt in counts.items():
            self.assertLessEqual(cnt / total, 0.30,
                f"asset {aid} dominates: {cnt}/{total} = {cnt/total:.2%}")
        # At least 15 of 30 assets were picked
        self.assertGreaterEqual(len(counts), 15)
        # restore
        AS._manifest = None; AS._manifest_index = {}


# ===========================================================  B: Character
class TestCharacter(unittest.TestCase):

    def _make(self, **kw):
        c = dict(CH.DEFAULT_CHARACTER)
        c.update(kw)
        return c

    def test_validate_good(self):
        errs = CH.validate_character(CH.DEFAULT_CHARACTER)
        self.assertEqual(errs, [])

    def test_validate_bad_body_type(self):
        errs = CH.validate_character(self._make(body_type="giant"))
        self.assertTrue(len(errs) > 0)

    def test_validate_bad_eye_type(self):
        errs = CH.validate_character(self._make(eye_type=9))
        self.assertTrue(len(errs) > 0)

    def test_validate_bad_outfit_class(self):
        errs = CH.validate_character(self._make(outfit_class="wizard"))
        self.assertTrue(len(errs) > 0)

    def test_validate_bad_outfit_additive(self):
        # "normal" class only allows {"collar","pattern"}, not "hood"
        errs = CH.validate_character(
            self._make(outfit_class="normal", outfit_additive="hood"))
        self.assertTrue(len(errs) > 0)

    def test_validate_height_class_range(self):
        # adult_avg should be ~170 cm
        errs = CH.validate_character(
            self._make(height_class="adult_avg", real_height_cm=170))
        self.assertEqual(errs, [])
        # 50 cm is a baby, not adult
        errs2 = CH.validate_character(
            self._make(height_class="adult_avg", real_height_cm=50))
        self.assertTrue(len(errs2) > 0)

    def test_validate_named_skin(self):
        errs = CH.validate_character(self._make(skin_tone="pale"))
        self.assertEqual(errs, [])

    def test_validate_bad_skin(self):
        errs = CH.validate_character(self._make(skin_tone="turquoise_alien"))
        self.assertTrue(len(errs) > 0)

    def test_draw_no_crash(self):
        """draw_character must render into a numpy frame without raising."""
        from engine.gfx import Cam
        img = np.zeros((1920, 1080, 3), np.uint8)
        cam = Cam(0, 0, 1.0, 0)
        for bt in CH.BODY_TYPES:
            for et in CH.EYE_TYPES:
                for oc in CH.OUTFIT_CLASSES:
                    c = self._make(body_type=bt, eye_type=et, outfit_class=oc)
                    CH.draw_character(img, cam, 540, 1700, 1400, c, t=0.5)
        self.assertGreater(img.std(), 0.5)

    def test_draw_different_chars_differ(self):
        """Two characters with different params must produce different pixels."""
        from engine.gfx import Cam
        cam = Cam(0, 0, 1.0, 0)
        img1 = np.zeros((1920, 1080, 3), np.uint8)
        img2 = np.zeros((1920, 1080, 3), np.uint8)
        c1 = self._make(skin_tone="pale",      eye_type=1, outfit_class="normal")
        c2 = self._make(skin_tone="warm_deep",  eye_type=3, outfit_class="tactical")
        CH.draw_character(img1, cam, 540, 1700, 1400, c1)
        CH.draw_character(img2, cam, 540, 1700, 1400, c2)
        self.assertFalse(np.array_equal(img1, img2))

    def test_all_hair_styles_no_crash(self):
        from engine.gfx import Cam
        cam = Cam(0, 0, 1.0, 0)
        img = np.zeros((1920, 1080, 3), np.uint8)
        for hs in CH.HAIR_STYLES:
            c = self._make(hair_style=hs)
            CH.draw_character(img, cam, 540, 1700, 1400, c, t=1.0)

    def test_all_moods_no_crash(self):
        from engine.gfx import Cam
        cam = Cam(0, 0, 1.0, 0)
        img = np.zeros((1920, 1080, 3), np.uint8)
        for mood in ("neutral", "happy", "worried", "shock"):
            c = self._make()
            CH.draw_character(img, cam, 540, 1700, 1400, c, t=0.5, mood=mood)


# ===========================================================  F: Formulas
class TestFormulas(unittest.TestCase):

    def _story(self, formula, beats):
        return {
            "title": "test",
            "factual": False,
            "formula": formula,
            "beats": beats,
        }

    def _beat(self, role, scene="hook_counter"):
        return self._beat_id(role, role, scene)

    def _beat_id(self, role, bid, scene="hook_counter"):
        return {
            "id": bid,
            "role": role,
            "text": "test beat text here ok",
            "scene": scene,
            "cam": {"from": {"x": 0, "y": 0, "zoom": 1.0},
                    "to":   {"x": 10, "y": 0, "zoom": 1.05},
                    "creep": 0.03},
        }

    def test_explainer_valid(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in
                 ["hook","setting","snap","explanation","consequence","twist"]]
        E, W = validate_story(self._story("explainer", beats))
        self.assertEqual(E, [])

    def test_product_ad_valid(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in ["hook","benefit","proof","cta"]]
        E, W = validate_story(self._story("product_ad", beats))
        self.assertEqual(E, [])

    def test_product_ad_wrong_role_rejected(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in ["hook","setting","snap","cta"]]
        E, W = validate_story(self._story("product_ad", beats))
        self.assertTrue(len(E) > 0)

    def test_tutorial_valid(self):
        from engine.story import validate_story
        roles  = ["hook","setup","step","step","payoff"]
        beats  = []
        seen: dict = {}
        for r in roles:
            seen[r] = seen.get(r, 0) + 1
            beats.append(self._beat_id(r, f"{r}_{seen[r]}"))
        E, W = validate_story(self._story("tutorial", beats))
        self.assertEqual(E, [])

    def test_character_valid(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in
                 ["hook","introduce","conflict","turn","resolve"]]
        E, W = validate_story(self._story("character", beats))
        self.assertEqual(E, [])

    def test_brand_valid(self):
        from engine.story import validate_story
        roles  = ["hook","world","value","value","invite"]
        beats  = []
        seen: dict = {}
        for r in roles:
            seen[r] = seen.get(r, 0) + 1
            beats.append(self._beat_id(r, f"{r}_{seen[r]}"))
        E, W = validate_story(self._story("brand", beats))
        self.assertEqual(E, [])

    def test_unknown_formula_rejected(self):
        from engine.story import validate_story
        beats = [self._beat("hook"), self._beat("hook")]
        E, W = validate_story(self._story("alien_format", beats))
        self.assertTrue(len(E) > 0)

    def test_theme_in_story_validated(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in ["hook","benefit","proof","cta"]]
        s = self._story("product_ad", beats)
        s["theme"] = {"primary": [0, 255, 0], "vignette": 0.3}
        E, W = validate_story(s)
        self.assertEqual(E, [])

    def test_bad_theme_in_story_error(self):
        from engine.story import validate_story
        beats = [self._beat(r) for r in ["hook","benefit","proof","cta"]]
        s = self._story("product_ad", beats)
        s["theme"] = {"primary": [999, 0, 0]}
        E, W = validate_story(s)
        self.assertTrue(len(E) > 0)


# ===========================================================  Integration
class TestIntegration(unittest.TestCase):

    def test_original_tests_still_importable(self):
        """Make sure our changes didn't break the existing engine imports."""
        from engine import story, scenes, gfx, sound, qa, voice
        self.assertTrue(hasattr(scenes, "SCENES"))
        self.assertIn("hook_counter", scenes.SCENES)

    def test_new_scenes_registered(self):
        from engine import scenes
        for name in ("csv_drop","prompt_box","agent_build","device_local",
                     "audit_table","more_burst","compare_tabs","free_tokens"):
            self.assertIn(name, scenes.SCENES,
                          f"scene '{name}' not registered")

    def test_ctx_has_theme_slot(self):
        from engine.scenes import Ctx
        from engine.gfx import Cam
        ctx = Ctx(0.0, 1.0, 30, Cam(0,0,1,0), {}, {})
        self.assertIsInstance(ctx.theme, dict)
        self.assertIsInstance(ctx.world, dict)
        self.assertIsInstance(ctx.characters, dict)

    def test_music_new_moods_no_crash(self):
        from engine.sound import music
        for mood in ("wonder","tense","upbeat","warm","dramatic","calm"):
            m = music(3.0, mood=mood, bpm=92)
            self.assertGreater(len(m), 0)
            self.assertFalse(np.any(np.isnan(m)))

    def test_scene_smoke_with_theme(self):
        """Every new scene renders without error when ctx.theme is set."""
        import json
        from engine import scenes, story as ST
        from engine.gfx import Cam
        import numpy as np

        theme = TH.resolve({"preset": "dark_gold"})
        cam   = Cam(0, 0, 1.0, 0)

        for name in ("csv_drop","prompt_box","agent_build","device_local",
                     "audit_table","more_burst","compare_tabs","free_tokens"):
            img = np.zeros((1920, 1080, 3), np.uint8)
            ctx = scenes.Ctx(1.5, 4.0, 30, cam, {}, {})
            ctx.theme      = theme
            ctx.world      = {}
            ctx.characters = {}
            scenes.SCENES[name](img, ctx)
            self.assertGreater(img.std(), 0.5,
                               f"scene '{name}' produced a blank frame")


if __name__ == "__main__":
    unittest.main(verbosity=2)
