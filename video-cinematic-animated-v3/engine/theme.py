"""theme.py - Theme system for video-cinematic v3.
Loads the story's optional `theme` block, fills defaults, validates, and
exposes a resolved dict that every scene reads via ctx.theme.
All colours are (R, G, B) tuples. No scene hardcodes a colour; it reads
ctx.theme["primary"] etc. so two stories with different themes look like
different shows.
"""
from __future__ import annotations
import copy

# ------------------------------------------------------------------ defaults
DEFAULT_THEME = {
    # backgrounds
    "bg_top":           (9,   13,  33),
    "bg_bot":           (30,  22,  72),
    # main palette
    "primary":          (72,  224, 172),   # mint
    "secondary":        (92,  200, 255),   # cyan
    "accent":           (255, 190,  82),   # amber
    "danger":           (255, 102, 114),   # coral
    "violet":           (162, 132, 255),
    # surfaces
    "card":             (30,  38,  86),
    "card2":            (42,  52,  112),
    "cell":             (36,  46,  100),
    "panel":            (22,  30,  70),
    "bar":              (96,  110, 168),
    # text
    "text":             (245, 246, 250),   # near-white
    "muted":            (150, 164, 208),
    "ink":              (20,  22,  46),    # dark for text on light bg
    # typography
    "font_dir":         "/usr/share/fonts/opentype/inter/",
    "font_display":     "InterDisplay",
    "font_body":        "Inter",
    # geometry
    "card_radius":      44,
    "shadow_offset":    (6,  10),
    "shadow_shade":     0.45,
    # post-process
    "vignette":         0.5,              # 0 = off, 1 = full
    # ambient particles
    "ambient_density":  36,
    "ambient_color":    (150, 180, 255),
    "ambient_speed":    45,
    "ambient_alpha":    0.5,
    # music
    "music_mood":       "wonder",
    "music_bpm":        92,
}

# Named preset themes the agent can reference by name
PRESETS = {
    "default": {},   # uses DEFAULT_THEME as-is

    "dark_gold": {
        "bg_top":    (10, 8,  22),
        "bg_bot":    (38, 28, 12),
        "primary":   (255, 200, 72),
        "secondary": (255, 160, 40),
        "accent":    (200, 240, 255),
        "card":      (32, 26, 14),
        "card2":     (48, 38, 18),
        "ambient_color": (255, 220, 120),
        "music_mood": "warm",
    },

    "clean_light": {
        "bg_top":    (230, 235, 250),
        "bg_bot":    (200, 212, 240),
        "primary":   (60,  120, 255),
        "secondary": (100, 180, 255),
        "accent":    (255, 100, 80),
        "card":      (255, 255, 255),
        "card2":     (240, 244, 255),
        "cell":      (225, 230, 248),
        "panel":     (210, 218, 240),
        "bar":       (160, 174, 210),
        "text":      (20,  22,  46),
        "muted":     (100, 112, 160),
        "ink":       (245, 246, 250),
        "ambient_color": (100, 140, 255),
        "ambient_alpha": 0.3,
        "music_mood": "upbeat",
    },

    "warm_earth": {
        "bg_top":    (28, 20, 14),
        "bg_bot":    (60, 38, 22),
        "primary":   (200, 160, 80),
        "secondary": (160, 200, 100),
        "accent":    (220, 100, 60),
        "card":      (48, 34, 20),
        "card2":     (64, 46, 28),
        "ambient_color": (220, 180, 100),
        "music_mood": "warm",
    },

    "neon_night": {
        "bg_top":    (4,   4,  16),
        "bg_bot":    (16,  4,  32),
        "primary":   (0,   255, 180),
        "secondary": (180, 0,   255),
        "accent":    (255, 60,  180),
        "card":      (20,  12,  40),
        "card2":     (32,  16,  56),
        "ambient_color": (100, 0, 255),
        "ambient_alpha": 0.8,
        "music_mood": "dramatic",
    },

    "corporate": {
        "bg_top":    (18, 24, 42),
        "bg_bot":    (10, 14, 30),
        "primary":   (60, 140, 255),
        "secondary": (40, 180, 220),
        "accent":    (255, 180, 0),
        "card":      (24, 32, 60),
        "card2":     (32, 44, 80),
        "music_mood": "calm",
    },
}


# ------------------------------------------------------------------ validation
def _validate_color(v, name):
    if not (isinstance(v, (list, tuple)) and len(v) == 3
            and all(isinstance(c, int) and 0 <= c <= 255 for c in v)):
        raise ValueError(f"theme.{name}: must be [R, G, B] with ints 0-255, got {v!r}")
    return tuple(v)


def _validate_number(v, name, lo, hi):
    if not isinstance(v, (int, float)) or not (lo <= v <= hi):
        raise ValueError(f"theme.{name}: must be a number {lo}–{hi}, got {v!r}")
    return float(v)


COLOR_KEYS = [
    "bg_top", "bg_bot", "primary", "secondary", "accent", "danger", "violet",
    "card", "card2", "cell", "panel", "bar", "text", "muted", "ink",
    "ambient_color",
]
NUMBER_KEYS = {
    "card_radius":     (0,   200),
    "vignette":        (0,   1),
    "ambient_density": (0,   200),
    "ambient_speed":   (1,   300),
    "ambient_alpha":   (0,   1),
    "shadow_shade":    (0,   1),
    "music_bpm":       (40,  200),
}
MUSIC_MOODS = {"wonder", "tense", "upbeat", "warm", "dramatic", "calm"}


def validate_theme(raw: dict) -> list[str]:
    """Return list of error strings (empty = valid)."""
    errors = []
    for k in COLOR_KEYS:
        if k in raw:
            try:
                _validate_color(raw[k], k)
            except ValueError as e:
                errors.append(str(e))
    for k, (lo, hi) in NUMBER_KEYS.items():
        if k in raw:
            try:
                _validate_number(raw[k], k, lo, hi)
            except ValueError as e:
                errors.append(str(e))
    if "music_mood" in raw and raw["music_mood"] not in MUSIC_MOODS:
        errors.append(
            f"theme.music_mood: '{raw['music_mood']}' not in {sorted(MUSIC_MOODS)}"
        )
    if "preset" in raw and raw["preset"] not in PRESETS:
        errors.append(
            f"theme.preset: '{raw['preset']}' not in {sorted(PRESETS)}"
        )
    return errors


# ------------------------------------------------------------------ resolve
def resolve(raw: dict | None) -> dict:
    """
    Merge raw theme block onto defaults and return a fully-resolved dict.
    If raw contains "preset", that preset is applied first (before raw overrides).
    All colour values are normalised to (R, G, B) tuples of ints.
    """
    base = copy.deepcopy(DEFAULT_THEME)
    if raw is None:
        return base

    # apply named preset first
    preset_name = raw.get("preset", "default")
    if preset_name in PRESETS:
        for k, v in PRESETS[preset_name].items():
            base[k] = v

    # apply explicit overrides
    for k, v in raw.items():
        if k == "preset":
            continue
        if k in COLOR_KEYS:
            base[k] = tuple(int(c) for c in v)
        elif k == "shadow_offset":
            base[k] = tuple(v)
        else:
            base[k] = v

    return base
