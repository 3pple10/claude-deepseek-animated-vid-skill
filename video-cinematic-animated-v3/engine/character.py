"""character.py - Morphic character system for video-cinematic v3.
Replaces the single hardcoded pip() shape with a fully parameterized builder.
Every dimension is expressed as a fraction of the character's height so it
scales correctly at any world-scale size.

Agent assigns:
  body_type, height_class, real_height_cm,
  skin_tone (from named palette), hair_color, hair_style,
  eye_type (1-6), outfit_class, outfit_color_primary,
  outfit_color_accent, outfit_additive (optional)

The renderer reads the character dict and draws the result.
"""
from __future__ import annotations
import math
import numpy as np
import cv2
from . import gfx
from .gfx import poly, circle, line, polyline, paper, glow, ease, clamp, lerp, mixc

# ------------------------------------------------------------------ palettes
# Agent picks a palette name; the validator ensures the RGB is within range.
SKIN_PALETTES = {
    "pale":        (255, 224, 196),
    "fair":        (255, 213, 180),
    "light":       (240, 196, 160),
    "medium_light":(220, 172, 130),
    "medium":      (196, 148, 100),
    "medium_dark": (168, 118,  72),
    "dark":        (130,  86,  44),
    "deep":        ( 90,  54,  22),
    "warm_deep":   ( 80,  48,  28),
    "cool_deep":   ( 60,  44,  52),
}

HAIR_STYLES = {"short", "long", "bun", "cap", "bald", "afro", "fade"}
OUTFIT_CLASSES = {"common", "normal", "trendy", "worker", "athletic", "tactical"}
OUTFIT_ADDITIVES = {
    "common":   set(),
    "normal":   {"collar", "pattern"},
    "trendy":   {"hood", "stripe", "logo"},
    "worker":   {"vest", "apron", "helmet"},
    "athletic": {"stripe", "number"},
    "tactical": {"collar", "badge", "belt"},
}
HEIGHT_CLASSES = {
    "baby":       (40,   65),
    "toddler":    (66,  100),
    "kid":        (101, 140),
    "teen":       (141, 164),
    "adult_short":(155, 164),
    "adult_avg":  (158, 178),
    "adult_tall": (179, 210),
}
BODY_TYPES = {"slim", "average", "sturdy", "broad"}
EYE_TYPES  = {1, 2, 3, 4, 5, 6}

DEFAULT_CHARACTER = {
    "id":                   "character",
    "body_type":            "average",
    "height_class":         "adult_avg",
    "real_height_cm":       170,
    "skin_tone":            "medium_light",
    "hair_color":           (60, 40, 20),
    "hair_style":           "short",
    "eye_type":             1,
    "outfit_class":         "normal",
    "outfit_color_primary": (60, 90, 180),
    "outfit_color_accent":  (200, 220, 255),
    "outfit_additive":      None,
}


# ------------------------------------------------------------------ validation
def validate_character(c: dict) -> list[str]:
    errors = []
    bt = c.get("body_type")
    if bt not in BODY_TYPES:
        errors.append(f"character.body_type '{bt}' not in {BODY_TYPES}")
    hc = c.get("height_class")
    if hc not in HEIGHT_CLASSES:
        errors.append(f"character.height_class '{hc}' not in {list(HEIGHT_CLASSES)}")
    if hc and "real_height_cm" in c:
        lo, hi = HEIGHT_CLASSES[hc]
        h = c["real_height_cm"]
        if not (lo - 5 <= h <= hi + 5):
            errors.append(
                f"character.real_height_cm {h} outside "
                f"height_class '{hc}' range {lo}-{hi} cm"
            )
    sk = c.get("skin_tone")
    if isinstance(sk, str) and sk not in SKIN_PALETTES:
        errors.append(
            f"character.skin_tone '{sk}' not in named palettes {list(SKIN_PALETTES)}; "
            f"or pass an [R,G,B] list"
        )
    hs = c.get("hair_style")
    if hs not in HAIR_STYLES:
        errors.append(f"character.hair_style '{hs}' not in {HAIR_STYLES}")
    et = c.get("eye_type")
    if et not in EYE_TYPES:
        errors.append(f"character.eye_type {et!r} not in {EYE_TYPES} (1-6)")
    oc = c.get("outfit_class")
    if oc not in OUTFIT_CLASSES:
        errors.append(f"character.outfit_class '{oc}' not in {OUTFIT_CLASSES}")
    oa = c.get("outfit_additive")
    if oa and oc in OUTFIT_ADDITIVES:
        allowed = OUTFIT_ADDITIVES[oc]
        # empty set means NO additives permitted for this class
        if oa not in allowed:
            errors.append(
                f"character.outfit_additive '{oa}' not allowed for "
                f"outfit_class '{oc}'; allowed: {allowed or '(none)'}"
            )
    return errors


# ------------------------------------------------------------------ body ratios
# All values are fractions of `h` (total pixel height of the character).
# body_type adjusts shoulder/hip width multipliers.
BODY_RATIOS = {
    #           shoulder_w  hip_w  torso_h  head_r  leg_h
    "slim":     (0.28,      0.22,  0.38,    0.15,   0.44),
    "average":  (0.34,      0.28,  0.38,    0.16,   0.42),
    "sturdy":   (0.42,      0.36,  0.40,    0.17,   0.40),
    "broad":    (0.50,      0.44,  0.42,    0.17,   0.38),
}


# ------------------------------------------------------------------ skin tone resolver
def _skin(c: dict) -> tuple:
    sk = c.get("skin_tone", "medium_light")
    if isinstance(sk, (list, tuple)) and len(sk) == 3:
        return tuple(int(x) for x in sk)
    return SKIN_PALETTES.get(sk, SKIN_PALETTES["medium_light"])


# ------------------------------------------------------------------ eye drawing
def _draw_eye(img, cam, cx, cy, s, eye_type, skin, t, blink, look):
    """Draw one eye. s = scale (pixels). look = (dx, dy) fraction."""
    INK = (20, 22, 46); WHITE = (245, 246, 250)
    if blink:
        line(img, cam.p(cx - 14*s, cy), cam.p(cx + 14*s, cy), INK, max(2, 4*s*cam.zoom))
        return
    if eye_type == 1:   # round (classic)
        circle(img, cam.p(cx, cy), 18*s*cam.zoom, WHITE)
        circle(img, cam.p(cx + look[0]*7*s, cy + look[1]*7*s), 9*s*cam.zoom, INK)
    elif eye_type == 2: # almond / narrow
        pts = [(cx + math.cos(a)*18*s, cy + math.sin(a)*10*s) for a in
               [i*math.pi/8 for i in range(16)]]
        poly(img, cam.pts(pts), WHITE)
        circle(img, cam.p(cx + look[0]*5*s, cy + look[1]*5*s), 7*s*cam.zoom, INK)
    elif eye_type == 3: # wide anime
        circle(img, cam.p(cx, cy), 24*s*cam.zoom, WHITE)
        circle(img, cam.p(cx + look[0]*8*s, cy + look[1]*8*s), 14*s*cam.zoom, INK)
        circle(img, cam.p(cx + look[0]*8*s - 5*s, cy + look[1]*8*s - 5*s), 4*s*cam.zoom, WHITE)
    elif eye_type == 4: # dot / simple
        circle(img, cam.p(cx, cy), 9*s*cam.zoom, INK)
    elif eye_type == 5: # rectangular / robot
        gfx.rrect(img, *[int(cam.p(cx, cy)[i//2] + d) for i, d in
                         enumerate([-16*s*cam.zoom, -10*s*cam.zoom,
                                     16*s*cam.zoom,  10*s*cam.zoom])],
                  3, (80, 240, 180))
    elif eye_type == 6: # closed / content
        polyline(img, cam.pts([(cx - 14*s, cy + 2*s), (cx, cy - 8*s),
                                (cx + 14*s, cy + 2*s)]), INK,
                 max(2, 4*s*cam.zoom))


# ------------------------------------------------------------------ hair drawing
def _draw_hair(img, cam, cx, cy, r, hair_col, style, s):
    if style == "bald":
        return
    hc = tuple(int(v*0.7) for v in hair_col)
    if style == "short":
        poly(img, cam.pts([(cx - r*0.9, cy - r*0.1),
                           (cx + r*0.9, cy - r*0.1),
                           (cx + r*0.7, cy - r*1.0),
                           (cx,         cy - r*1.25),
                           (cx - r*0.7, cy - r*1.0)]), hair_col)
    elif style == "long":
        poly(img, cam.pts([(cx - r*0.9, cy - r*0.1),
                           (cx + r*0.9, cy - r*0.1),
                           (cx + r*0.8, cy - r*1.0),
                           (cx,         cy - r*1.3),
                           (cx - r*0.8, cy - r*1.0)]), hair_col)
        poly(img, cam.pts([(cx - r*0.9, cy + r*0.2),
                           (cx - r*1.1, cy + r*2.5),
                           (cx - r*0.4, cy + r*2.5)]), hair_col)
        poly(img, cam.pts([(cx + r*0.9, cy + r*0.2),
                           (cx + r*1.1, cy + r*2.5),
                           (cx + r*0.4, cy + r*2.5)]), hair_col)
    elif style == "bun":
        poly(img, cam.pts([(cx - r*0.9, cy - r*0.1),
                           (cx + r*0.9, cy - r*0.1),
                           (cx + r*0.7, cy - r*1.0),
                           (cx - r*0.7, cy - r*1.0)]), hair_col)
        circle(img, cam.p(cx, cy - r*1.3), int(r*0.55*cam.zoom), hair_col)
    elif style == "cap":
        poly(img, cam.pts([(cx - r*1.1, cy - r*0.05),
                           (cx + r*1.1, cy - r*0.05),
                           (cx + r*0.9, cy - r*0.9),
                           (cx - r*0.9, cy - r*0.9)]), hc)
        poly(img, cam.pts([(cx - r*0.9, cy - r*0.9),
                           (cx + r*0.9, cy - r*0.9),
                           (cx + r*0.7, cy - r*1.3),
                           (cx - r*0.7, cy - r*1.3)]), hair_col)
    elif style == "afro":
        for dx, dy, rr in ((-0.3, -1.1, 0.75), (0.3, -1.1, 0.75),
                           (0, -1.4, 0.65), (0, -0.7, 0.60)):
            circle(img, cam.p(cx + dx*r, cy + dy*r), int(rr*r*cam.zoom), hair_col)
    elif style == "fade":
        poly(img, cam.pts([(cx - r*0.9, cy + r*0.1),
                           (cx + r*0.9, cy + r*0.1),
                           (cx + r*0.7, cy - r*0.6),
                           (cx - r*0.7, cy - r*0.6)]), hc)
        poly(img, cam.pts([(cx - r*0.7, cy - r*0.6),
                           (cx + r*0.7, cy - r*0.6),
                           (cx + r*0.5, cy - r*1.1),
                           (cx - r*0.5, cy - r*1.1)]), hair_col)


# ------------------------------------------------------------------ outfit drawing
def _draw_outfit(img, cam, cx, cy, h, sw, hw, th,
                 outfit_class, primary, accent, additive):
    """
    Draw outfit on body.
    cx, cy  = character center-x, hip-y reference
    sw, hw  = shoulder width, hip width (pixels)
    th      = torso height (pixels)
    """
    neck_y = cy - th
    shoulder_y = neck_y + th * 0.08
    # torso silhouette
    torso = [(cx - sw/2, shoulder_y),
             (cx + sw/2, shoulder_y),
             (cx + hw/2, cy),
             (cx - hw/2, cy)]

    if outfit_class == "common":
        return  # skin only

    if outfit_class == "normal":
        paper(img, cam.pts(torso), primary, off=(4*cam.zoom, 6*cam.zoom))
        # collar hint
        if additive == "collar":
            pts = [(cx - sw*0.2, shoulder_y),
                   (cx + sw*0.2, shoulder_y),
                   (cx, shoulder_y + th*0.12)]
            poly(img, cam.pts(pts), accent)

    elif outfit_class == "trendy":
        paper(img, cam.pts(torso), primary, off=(4*cam.zoom, 6*cam.zoom))
        # hood silhouette behind head
        if additive == "hood":
            poly(img, cam.pts([
                (cx - sw*0.45, shoulder_y - th*0.05),
                (cx + sw*0.45, shoulder_y - th*0.05),
                (cx + sw*0.5,  shoulder_y + th*0.1),
                (cx - sw*0.5,  shoulder_y + th*0.1),
            ]), tuple(int(v*0.75) for v in primary))
        if additive == "stripe":
            line(img, cam.p(cx - sw*0.42, shoulder_y),
                      cam.p(cx - sw*0.42, cy), accent,
                      max(2, int(sw*0.08*cam.zoom)))
            line(img, cam.p(cx + sw*0.42, shoulder_y),
                      cam.p(cx + sw*0.42, cy), accent,
                      max(2, int(sw*0.08*cam.zoom)))

    elif outfit_class == "worker":
        paper(img, cam.pts(torso), primary, off=(4*cam.zoom, 6*cam.zoom))
        if additive == "vest":
            vest = [(cx - sw*0.4, shoulder_y + th*0.05),
                    (cx + sw*0.4, shoulder_y + th*0.05),
                    (cx + sw*0.35, cy - th*0.05),
                    (cx - sw*0.35, cy - th*0.05)]
            poly(img, cam.pts(vest), accent)
        if additive == "helmet":
            # drawn above head; caller handles head first so this is OK
            poly(img, cam.pts([
                (cx - sw*0.55, neck_y - th*0.52),
                (cx + sw*0.55, neck_y - th*0.52),
                (cx + sw*0.5,  neck_y - th*0.70),
                (cx - sw*0.5,  neck_y - th*0.70),
            ]), accent)

    elif outfit_class == "athletic":
        paper(img, cam.pts(torso), primary, off=(3*cam.zoom, 5*cam.zoom))
        if additive == "stripe":
            for sx in (-0.44, 0.44):
                line(img, cam.p(cx + sw*sx, shoulder_y),
                          cam.p(cx + sw*sx, cy), accent,
                          max(2, int(sw*0.06*cam.zoom)))

    elif outfit_class == "tactical":
        paper(img, cam.pts(torso), primary, off=(5*cam.zoom, 8*cam.zoom))
        # structured collar
        poly(img, cam.pts([
            (cx - sw*0.18, shoulder_y),
            (cx + sw*0.18, shoulder_y),
            (cx + sw*0.14, shoulder_y + th*0.14),
            (cx - sw*0.14, shoulder_y + th*0.14),
        ]), tuple(int(v*0.75) for v in primary))
        if additive == "badge":
            circle(img, cam.p(cx - sw*0.28, shoulder_y + th*0.22),
                   int(sw*0.09*cam.zoom), accent)
        if additive == "belt":
            by = cy - th*0.08
            poly(img, cam.pts([
                (cx - hw*0.52, by - th*0.04),
                (cx + hw*0.52, by - th*0.04),
                (cx + hw*0.52, by + th*0.04),
                (cx - hw*0.52, by + th*0.04),
            ]), accent)


# ------------------------------------------------------------------ main draw
def draw_character(
    img,
    cam,
    cx: float,
    cy_bottom: float,
    px_height: float,
    char: dict,
    t:    float = 0.0,
    mood: str   = "neutral",
    look: tuple = (0, 0),
    arm_l: float = 0.0,
    arm_r: float = 0.0,
    seed: int   = 0,
) -> None:
    """
    Draw a fully parameterized morphic character.

    cx          : screen X centre of character
    cy_bottom   : screen Y where the character's feet touch the ground
    px_height   : total pixel height of the character
    char        : character parameter dict (from story.json characters block)
    t           : time within beat (seconds) — drives idle animation
    mood        : neutral | happy | worried | shock
    look        : (dx, dy) eye direction fractions (-1 to 1)
    arm_l/r     : arm angle in radians
    seed        : deterministic random seed for per-character animation phase
    """
    h    = px_height
    bt   = char.get("body_type", "average")
    sw_f, hw_f, th_f, hr_f, leg_f = BODY_RATIOS.get(bt, BODY_RATIOS["average"])

    sw   = h * sw_f    # shoulder width px
    hw   = h * hw_f    # hip width px
    th   = h * th_f    # torso height px
    hr   = h * hr_f    # head radius px
    leg  = h * leg_f   # leg height px

    skin       = _skin(char)
    hair_col   = tuple(char.get("hair_color", (60, 40, 20)))
    eye_type   = char.get("eye_type", 1)
    outfit_cls = char.get("outfit_class", "normal")
    primary    = tuple(char.get("outfit_color_primary", (60, 90, 180)))
    accent     = tuple(char.get("outfit_color_accent", (200, 220, 255)))
    additive   = char.get("outfit_additive")

    # idle bob
    bob = math.sin(t * 3.0 + seed * 1.37) * h * 0.012

    # reference points
    feet_y     = cy_bottom + bob
    hip_y      = feet_y - leg
    shoulder_y = hip_y - th
    neck_y     = shoulder_y
    head_cy    = neck_y - hr * 0.6

    s = hr / 92.0   # scale factor relative to default head radius

    # ---- shadow
    shadow_w = sw * 1.1 * cam.zoom
    sx, sy = cam.p(cx, feet_y + hr * 0.15)
    pts_sh = [(sx - shadow_w, sy), (sx + shadow_w, sy),
              (sx + shadow_w * 0.7, sy + hr * 0.18 * cam.zoom),
              (sx - shadow_w * 0.7, sy + hr * 0.18 * cam.zoom)]
    poly(img, pts_sh, (0, 0, 0))
    # make it semi-transparent by redrawing with original colour at 60%
    roi = img[max(0,int(sy-hr*0.25)):int(sy+hr*0.3),
              max(0,int(sx-shadow_w)):int(sx+shadow_w)]
    if roi.size:
        img[max(0,int(sy-hr*0.25)):int(sy+hr*0.3),
            max(0,int(sx-shadow_w)):int(sx+shadow_w)] = \
            (roi.astype(np.float32) * 0.4).astype(np.uint8)

    # ---- legs
    knee_y = hip_y + leg * 0.52
    for sx_f in (-0.26, 0.26):
        lx = cx + hw * sx_f
        line(img, cam.p(lx, hip_y), cam.p(lx * 0.98, knee_y),
             tuple(int(v * 0.7) for v in skin), max(2, int(hw * 0.22 * cam.zoom)))
        line(img, cam.p(lx * 0.98, knee_y), cam.p(lx * 1.0, feet_y),
             tuple(int(v * 0.7) for v in skin), max(2, int(hw * 0.20 * cam.zoom)))
        # shoe hint
        poly(img, cam.pts([(lx - hw*0.14, feet_y),
                           (lx + hw*0.18, feet_y),
                           (lx + hw*0.18, feet_y + leg*0.06),
                           (lx - hw*0.14, feet_y + leg*0.06)]),
             tuple(int(v*0.4) for v in primary))

    # ---- outfit torso (drawn before arms for occlusion)
    _draw_outfit(img, cam, cx, hip_y, h, sw, hw, th,
                 outfit_cls, primary, accent, additive)

    # ---- arms
    for side, ang in ((-1, arm_l), (1, arm_r)):
        ax0, ay0 = cam.p(cx + side * sw * 0.46, shoulder_y + th * 0.1)
        aex = side * (sw * 0.46 + hw * 0.4 * math.cos(ang))
        aey = th * 0.1 + hw * 0.7 * math.sin(ang)
        ax1, ay1 = cam.p(cx + aex, shoulder_y + aey)
        line(img, (ax0, ay0), (ax1, ay1), skin,
             max(2, int(sw * 0.14 * cam.zoom)))
        circle(img, (ax1, ay1), int(sw * 0.11 * cam.zoom), skin)

    # ---- head background (for hair behind)
    _draw_hair(img, cam, cx, head_cy, hr, hair_col,
               char.get("hair_style", "short"), s)

    # ---- head
    head_shadow = tuple(int(v * 0.6) for v in skin)
    circle(img, cam.p(cx + hr*0.07, head_cy + hr*0.09), int(hr*cam.zoom), head_shadow)
    circle(img, cam.p(cx, head_cy), int(hr * cam.zoom), skin)

    # ---- cap-style hair overlay (after head so it's on top)
    if char.get("hair_style") == "cap":
        _draw_hair(img, cam, cx, head_cy, hr, hair_col, "cap", s)

    # ---- eyes
    blink = math.sin(t * 1.9 + seed * 2.7) > 0.97
    ey_offset = hr * (-0.26 if mood != "shock" else -0.32)
    for ex_f in (-0.36, 0.36):
        _draw_eye(img, cam, cx + hr * ex_f, head_cy + ey_offset,
                  s, eye_type, skin, t, blink, look)

    # ---- eyebrows
    INK = (20, 22, 46)
    brow_lift = {"worried": (-0.12, 0.12), "happy": (0.08, 0.08),
                 "shock": (-0.18, -0.18), "neutral": (0, 0)}.get(mood, (0, 0))
    for side in (-1, 1):
        bo = brow_lift[0] if side < 0 else brow_lift[1]
        bx0 = cx + side * hr * 0.56
        bx1 = cx + side * hr * 0.14
        by  = head_cy + ey_offset - hr * (0.38 + bo)
        line(img, cam.p(bx0, by + hr * bo * 0.5 * side * 0.2),
                  cam.p(bx1, by),
             INK, max(1, int(hr * 0.07 * cam.zoom)))

    # ---- mouth
    mx, my = cx, head_cy + hr * 0.22
    if mood == "happy":
        polyline(img, cam.pts([
            (mx + math.cos(math.radians(a)) * hr * 0.26,
             my + math.sin(math.radians(a)) * hr * 0.20)
            for a in range(20, 161, 20)
        ]), INK, max(1, int(hr * 0.055 * cam.zoom)))
    elif mood == "shock":
        circle(img, cam.p(mx, my), int(hr * 0.14 * cam.zoom), INK)
    elif mood == "worried":
        polyline(img, cam.pts([
            (mx - hr*0.24, my + hr*0.08),
            (mx,           my - hr*0.02),
            (mx + hr*0.24, my + hr*0.08),
        ]), INK, max(1, int(hr * 0.055 * cam.zoom)))
    else:
        line(img, cam.p(mx - hr*0.20, my),
                  cam.p(mx + hr*0.20, my),
             INK, max(1, int(hr * 0.055 * cam.zoom)))
