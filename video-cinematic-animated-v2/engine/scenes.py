"""scenes.py - original scene library. Every scene: fn(img, ctx). Style: cut-paper layers, soft shadows, glow."""
import math
import numpy as np
from . import gfx
from .gfx import W, H, poly, circle, line, polyline, paper, glow, text, rrect, rrect_pts, ease, clamp, lerp, mixc

SCENES = {}
def scene(name):
    def deco(fn):
        SCENES[name] = fn
        return fn
    return deco

NAVY, PURP = (9, 11, 32), (46, 18, 70)
GOLD, GOLD2 = (232, 188, 84), (252, 226, 150)
WHITE, INK = (245, 246, 250), (24, 20, 40)
GREEN, REDC, ORANGE, BLUE = (70, 210, 140), (255, 84, 84), (255, 150, 60), (80, 160, 255)

_rng = np.random.default_rng(11)
STARS = np.c_[_rng.uniform(-2600, 2600, 320), _rng.uniform(-3600, 3600, 320), _rng.uniform(0.05, 0.6, 320),
              _rng.uniform(0.8, 2.6, 320), _rng.uniform(0, 6.28, 320)]


def space_bg(img, cam, t, top=NAVY, bot=PURP):
    img[:] = gfx.gradient(top, bot)
    for x, y, d, s, ph in STARS:
        px = (x - cam.x * d) * cam.zoom ** 0.35 + W / 2 + cam.sx * 0.3
        py = (y - cam.y * d) * cam.zoom ** 0.35 + H / 2 + cam.sy * 0.3
        px = (px - W / 2) % (W + 80) - 40 + 0
        py = (py - H / 2) % (H + 80) - 40
        b = int(150 + 105 * math.sin(t * 2 + ph))
        if s > 1.7:
            circle(img, (px, py), s, (b, b, min(255, b + 20)))
        else:
            xi, yi = int(px), int(py)
            if 0 <= xi < W and 0 <= yi < H:
                img[yi, xi] = (b, b, b)


def spacecraft(img, cam, x, y, s=1.0, ang=0.0, flame=0.0, t=0.0, split=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    def T(pts, dx=0, dy=0):
        return cam.pts([(x + (px * s + dx) * ca - (py * s + dy) * sa, y + (px * s + dx) * sa + (py * s + dy) * ca) for px, py in pts])
    # solar panels
    for side in (-1, 1):
        sd = split * 140 * side
        pts = T([(side * 70, -22), (side * 330, -22), (side * 330, 22), (side * 70, 22)], sd, split * 40 * side)
        paper(img, pts, (36, 84, 190), off=(4, 7))
        for i in range(1, 5):
            xx = side * (70 + i * 52)
            polyline(img, T([(xx, -22), (xx, 22)], sd, split * 40 * side), (120, 170, 245), max(1, 2 * cam.zoom))
        polyline(img, T([(side * 70, 0), (side * 330, 0)], sd, split * 40 * side), (120, 170, 245), max(1, 2 * cam.zoom))
    body = T([(-70, -60), (70, -60), (70, 60), (-70, 60)], 0, -split * 30)
    paper(img, body, GOLD)
    poly(img, T([(-70, -60), (70, -60), (70, -30), (-70, -30)], 0, -split * 30), GOLD2)
    c = cam.p(x, y - 90 * s)
    circle(img, c, 34 * s * cam.zoom, (210, 214, 224)); circle(img, c, 18 * s * cam.zoom, (150, 156, 170))
    if flame > 0:
        f = flame * (0.8 + 0.2 * math.sin(t * 40))
        poly(img, T([(-26, 60), (26, 60), (0, 60 + 150 * f)]), (255, 170, 60))
        poly(img, T([(-14, 60), (14, 60), (0, 60 + 90 * f)]), (255, 240, 170))
        glow(img, cam.p(x, y + 70 * s), 140 * s * cam.zoom * f, (255, 160, 70), 0.5)


def planet(img, cam, x, y, r, base, light, depth=0.8, atm=None, patches=None):
    c = cam.p(x, y, depth); rr = cam.r(r)
    if atm:
        glow(img, c, rr * 1.35, atm, 0.55)
    circle(img, c, rr, tuple(int(v * 0.55) for v in base))
    def fill(tmp):
        circle(tmp, c, rr, base)
        for (dx, dy, pr, col) in (patches or []):
            circle(tmp, (c[0] + dx * rr, c[1] + dy * rr), pr * rr, col)
        circle(tmp, (c[0] - 0.22 * rr, c[1] - 0.26 * rr), rr * 0.9, light)
        circle(tmp, (c[0] + 0.30 * rr, c[1] + 0.34 * rr), rr * 1.05, tuple(int(v * 0.6) for v in base))
        circle(tmp, (c[0] - 0.1 * rr, c[1] - 0.12 * rr), rr * 0.92, base)
    gfx.clip_circle(img, c, rr, fill)


def pip(img, cam, x, y, s, col, mood="neutral", t=0.0, look=(0, 0), armL=0.0, armR=0.0, seed=0, depth=1.0):
    """our character: a round-headed 'Pip' with big eyes, stick arms, soft shadow."""
    bob = math.sin(t * 3 + seed) * 5 * s
    P = lambda px, py: cam.p(x + px * s, y + py * s + bob, depth)
    k = cam.zoom * s
    paper(img, [P(-60, 40), P(60, 40), P(78, 190), P(-78, 190)], col, off=(6, 8))
    poly(img, [P(-60, 40), P(60, 40), P(66, 80), P(-66, 80)], mixc(col, (255, 255, 255), 0.25))
    for side, a in ((-1, armL), (1, armR)):
        sx0, sy0 = P(side * 62, 70); ex = side * (110 + 30 * math.cos(a)); ey = 70 + 120 * math.sin(a) - 40
        ex_, ey_ = P(ex, ey)
        line(img, (sx0, sy0), (ex_, ey_), mixc(col, (0, 0, 0), 0.25), 16 * k)
        circle(img, (ex_, ey_), 17 * k, (255, 224, 190))
    hc = P(0, -30)
    circle(img, (hc[0] + 6 * k, hc[1] + 9 * k), 92 * k, tuple(int(v * 0.6) for v in col))
    circle(img, hc, 92 * k, (255, 224, 190))
    circle(img, (hc[0], hc[1] - 18 * k), 92 * k * 0.9, mixc(col, (20, 20, 40), 0.35)) if mood == "cap" else None
    blink = (math.sin(t * 1.7 + seed * 3) > 0.985)
    ey = -42 if mood != "shock" else -48
    for ex in (-34, 34):
        c = P(ex, ey)
        if blink:
            line(img, (c[0] - 16 * k, c[1]), (c[0] + 16 * k, c[1]), INK, 5 * k)
        else:
            circle(img, c, (24 if mood == "shock" else 21) * k, WHITE)
            circle(img, (c[0] + look[0] * 8 * k, c[1] + look[1] * 8 * k), (7 if mood == "shock" else 11) * k, INK)
    brow = {"worried": (-12, 12), "happy": (8, 8), "shock": (-16, -16), "neutral": (0, 0)}.get(mood, (0, 0))
    for side, bo in ((-1, brow[0]), (1, brow[1])):
        a, b = P(side * 56, ey - 36 + bo * (1 if side < 0 else -1) * 0.2), P(side * 14, ey - 36 - bo * 0.0)
        line(img, a, b, INK, 6 * k)
    m = P(0, 22)
    if mood == "happy":
        polyline(img, [(m[0] + math.cos(math.radians(a)) * 26 * k, m[1] - 6 * k + math.sin(math.radians(a)) * 20 * k) for a in range(20, 161, 20)], INK, 5 * k)
    elif mood == "shock":
        circle(img, m, 15 * k, INK)
    elif mood == "worried":
        polyline(img, [(m[0] - 24 * k, m[1] + 8 * k), (m[0], m[1] - 2 * k), (m[0] + 24 * k, m[1] + 8 * k)], INK, 5 * k)
    else:
        line(img, (m[0] - 20 * k, m[1]), (m[0] + 20 * k, m[1]), INK, 5 * k)


def counter_text(v):
    return f"{int(v):,}"


# ------------------------------------------------------------------ scenes
@scene("hook_counter")
def hook_counter(img, ctx):
    cam, t = ctx.cam, ctx.t
    space_bg(img, cam, t)
    gfx.ambient(img, t, 30, 6, speed=40)
    hit = ctx.since("hit")
    val = ctx.p.get("value", 125_000_000) * ease(t / 1.1)
    split = ease((hit or -1) / 0.7) if hit is not None and hit > 0 else 0.0
    spacecraft(img, cam, 0, 120, 1.15, math.sin(t * 0.9) * 0.08 + 0.1 * split, flame=0.0, t=t, split=split)
    glow(img, cam.p(0, 120, 1), 420 * cam.zoom, (90, 120, 255), 0.18)
    col = mixc(WHITE, REDC, clamp((hit or 0) / 0.3)) if hit is not None and hit > 0 else WHITE
    text(img, "$" + counter_text(val), (W / 2 + (6 * math.sin(t * 80) if hit and 0 < hit < 0.4 else 0), 430 - 40 * split), 128, col)
    text(img, ctx.p.get("label", "SPACECRAFT"), (W / 2, 280), 42, (170, 180, 220), "SemiBold", alpha=ease(t / 0.6))
    if hit is not None and hit > 0:
        a = ease(hit / 0.25)
        pts = [(W / 2, 120)]
        rr = np.random.default_rng(3)
        for i in range(7):
            pts.append((pts[-1][0] + rr.uniform(-90, 90) * a, pts[-1][1] + 190 * a))
        polyline(img, pts, REDC, 9)


@scene("launch")
def launch(img, ctx):
    cam, t = ctx.cam, ctx.t
    t0 = ctx.p.get("liftoff", 0.7)
    ry = -0.5 * 250 * max(0.0, t - t0) ** 2
    alt = clamp(-ry / 2600)
    img[:] = gfx.gradient(mixc((255, 150, 110), NAVY, clamp(alt * 1.4)), mixc((255, 205, 150), (60, 80, 170), clamp(alt * 1.1)))
    if alt > 0.35:
        space_bg_overlay = clamp((alt - 0.35) * 2)
        for x, y, d, s, ph in STARS[:120]:
            px, py = (x % W), ((y - cam.y * 0.2) % H)
            circle(img, (px, py), s, (int(255 * space_bg_overlay),) * 3)
    g = cam.p(0, 0.0)[1] + 0
    for i, (col, off, hh) in enumerate(((mixc((60, 90, 110), (20, 24, 50), alt), 340, 90), (mixc((40, 70, 80), (14, 18, 40), alt), 400, 60))):
        pts = [cam.p(-900, 340 + hh + 300), cam.p(-900, 340 - hh * 0.2)]
        for k in range(0, 19):
            xx = -900 + k * 100
            pts.append(cam.p(xx, off - hh * (0.5 + 0.5 * math.sin(k * 0.9 + i))))
        pts += [cam.p(900, 340 - hh * 0.2), cam.p(900, 340 + hh + 300)]
        poly(img, pts, col)
    paper(img, [cam.p(-900, 330), cam.p(900, 330), cam.p(900, 900), cam.p(-900, 900)], mixc((70, 150, 90), (20, 40, 50), alt))
    paper(img, [cam.p(-260, 330), cam.p(-120, 330), cam.p(-120, -250), cam.p(-260, -250)], (110, 116, 140))
    for i in range(6):
        yy = 300 - i * 90
        polyline(img, [cam.p(-260, yy), cam.p(-120, yy - 90)], (80, 86, 110), 3)
    # smoke
    for i in range(40):
        bt = t0 + i * 0.06
        if t < bt:
            continue
        age = t - bt
        px = (-1 if i % 2 else 1) * (30 + 220 * age ** 0.7) * (0.5 + (i % 5) / 6)
        py = 330 - 60 * age
        glow(img, cam.p(px, py), cam.r(70 + 150 * age), (235, 235, 240), clamp(0.8 - age * 0.45))
    # rocket
    rx = 0
    body = [cam.p(rx - 45, ry + 140), cam.p(rx + 45, ry + 140), cam.p(rx + 45, ry - 140), cam.p(rx - 45, ry - 140)]
    paper(img, body, WHITE)
    paper(img, [cam.p(rx - 45, ry - 140), cam.p(rx + 45, ry - 140), cam.p(rx, ry - 230)], (230, 70, 70))
    paper(img, [cam.p(rx - 45, ry + 60), cam.p(rx - 95, ry + 150), cam.p(rx - 45, ry + 140)], (230, 70, 70))
    paper(img, [cam.p(rx + 45, ry + 60), cam.p(rx + 95, ry + 150), cam.p(rx + 45, ry + 140)], (230, 70, 70))
    circle(img, cam.p(rx, ry - 60), cam.r(22), (90, 150, 220))
    if t > t0:
        f = clamp((t - t0) / 0.4)
        poly(img, [cam.p(rx - 38, ry + 140), cam.p(rx + 38, ry + 140), cam.p(rx, ry + 140 + 260 * f * (0.85 + 0.15 * math.sin(t * 50)))], (255, 170, 60))
        poly(img, [cam.p(rx - 20, ry + 140), cam.p(rx + 20, ry + 140), cam.p(rx, ry + 140 + 140 * f)], (255, 245, 180))
        glow(img, cam.p(rx, ry + 170), cam.r(260) * f, (255, 170, 80), 0.55)
    # calendar sticker (screen-locked)
    k = ease((t - 0.2) / 0.35)
    ov = 1 + 0.12 * math.sin(clamp((t - 0.2) / 0.35) * math.pi)
    if k > 0:
        cx, cy, w, h = 230, 250, 340 * k * ov, 220 * k * ov
        paper(img, rrect_pts(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 26), WHITE)
        paper(img, rrect_pts(cx - w / 2, cy - h / 2, cx + w / 2, cy - h / 2 + 70 * k, 26), (220, 60, 70), off=(0, 0))
        text(img, ctx.p.get("month", "DEC"), (cx, cy - h / 2 + 36 * k), 44 * k, WHITE)
        text(img, ctx.p.get("year", "1998"), (cx, cy + 36 * k), 92 * k, INK)


@scene("space_cruise")
def space_cruise(img, ctx):
    cam, t, d = ctx.cam, ctx.t, ctx.d
    u = clamp(t / d)
    space_bg(img, cam, t)
    ex, ey, mx, my = -420, 700, 430, -720
    planet(img, cam, ex, ey, 200 * (1 - 0.55 * u), (50, 120, 210), (120, 200, 240), 0.7, (90, 150, 255),
           [(-0.3, 0.1, 0.3, (60, 170, 110)), (0.3, -0.35, 0.22, (60, 170, 110))])
    planet(img, cam, mx, my, 70 + 120 * u, (200, 90, 60), (240, 150, 100), 0.7, (255, 140, 90),
           [(-0.25, 0.2, 0.25, (160, 66, 46)), (0.3, -0.1, 0.18, (160, 66, 46))])
    def bez(k):
        a, b, c = (ex + 150, ey - 170), (-600, -100), (mx - 120, my + 120)
        return ((1 - k) ** 2 * a[0] + 2 * (1 - k) * k * b[0] + k * k * c[0], (1 - k) ** 2 * a[1] + 2 * (1 - k) * k * b[1] + k * k * c[1])
    for i in range(0, 60):
        k = i / 60
        if k < u:
            circle(img, cam.p(*bez(k)), cam.r(4), (190, 200, 255))
    x, y = bez(u); x2, y2 = bez(min(1, u + 0.01))
    ang = math.atan2(y2 - y, x2 - x) + math.pi / 2 * 0
    spacecraft(img, cam, x, y, 0.55, ang * 0.3, flame=0.0, t=t)
    k = ease((t - 0.4) / 0.4)
    if k > 0:
        paper(img, rrect_pts(W / 2 - 260 * k, 1560 - 60 * k, W / 2 + 260 * k, 1560 + 60 * k, 30), (30, 34, 80))
        text(img, ctx.p.get("tag", "10 MONTHS"), (W / 2, 1560), 56 * k, WHITE)


@scene("mission_control")
def mission_control(img, ctx):
    cam, t = ctx.cam, ctx.t
    img[:] = gfx.gradient((28, 32, 74), (52, 40, 96))
    for i in range(7):
        circle(img, cam.p(-420 + i * 140, -520 + 40 * math.sin(i), 0.3), cam.r(26), (60, 66, 130))
    paper(img, [cam.p(-900, 360), cam.p(900, 360), cam.p(900, 900), cam.p(-900, 900)], (36, 38, 84))
    for side, col, name in ((-1, (255, 150, 70), "BUILDERS"), (1, (90, 190, 230), "NAVIGATORS")):
        dx = side * 270
        paper(img, [cam.p(dx - 220, 280), cam.p(dx + 220, 280), cam.p(dx + 220, 330), cam.p(dx - 220, 330)], (92, 70, 60))
        pip(img, cam, dx, -60, 1.25, col, ctx.mood(side, t), t, (side * -0.6, 0.2), 0.2 * math.sin(t * 4 + side), 0.1, seed=side)
        mx0, my0 = cam.p(dx, 120), 0
        paper(img, rrect_pts(*(cam.p(dx - 110, 150) + cam.p(dx + 110, 280)), 14), (22, 24, 50))
        text(img, name, cam.p(dx, 380), cam.r(34), (180, 190, 240), "SemiBold")
    # note flying left -> right, repeated
    cyc = 2.0
    ph = (t % cyc) / cyc
    nx = lerp(-190, 190, ease(ph)); ny = -140 - 120 * math.sin(ph * math.pi)
    pc = cam.p(nx, ny)
    paper(img, rrect_pts(pc[0] - cam.r(62), pc[1] - cam.r(40), pc[0] + cam.r(62), pc[1] + cam.r(40), 10), WHITE, off=(4, 6))
    text(img, "100", (pc[0], pc[1] - cam.r(6)), cam.r(40), INK)
    text(img, ctx.p.get("tiny", "lbf·s"), (pc[0], pc[1] + cam.r(24)), cam.r(14), (170, 170, 190), "Regular")
    # right monitor shows a happy check once a note arrived
    if t > 1.0:
        mc = cam.p(270, 215)
        text(img, "100", (mc[0] - cam.r(30), mc[1]), cam.r(46), (150, 255, 190))
        k = ease((t - 1.0) / 0.3)
        polyline(img, [(mc[0] + cam.r(40), mc[1]), (mc[0] + cam.r(60), mc[1] + cam.r(20) * k), (mc[0] + cam.r(100), mc[1] - cam.r(30) * k)], GREEN, 8 * cam.zoom)


@scene("mars_approach")
def mars_approach(img, ctx):
    cam, t, d = ctx.cam, ctx.t, ctx.d
    space_bg(img, cam, t)
    loss = ctx.since("loss")
    mc, R = (280, 560), 520
    planet(img, cam, mc[0], mc[1], R, (200, 90, 60), (240, 150, 100), 0.9, (255, 150, 100),
           [(-0.3, 0.25, 0.28, (160, 66, 46)), (0.35, -0.2, 0.2, (160, 66, 46)), (0.0, 0.5, 0.16, (170, 80, 56))])
    glow(img, cam.p(*mc, 0.9), cam.r(R * 1.14), (255, 170, 120), 0.35)
    # planned vs actual paths (radius vs angle spiral)
    def path(u, r0, r1, a0=215, a1=300):
        r = lerp(r0, r1, ease(u)); a = math.radians(lerp(a0, a1, u))
        return (mc[0] + r * math.cos(a), mc[1] + r * math.sin(a))
    for i in range(0, 50):
        u = i / 50
        circle(img, cam.p(*path(u, 900, 720)), cam.r(5), GREEN)
        if u * d * 0.95 < t:
            circle(img, cam.p(*path(u, 900, 548)), cam.r(5), REDC)
    u = clamp(t / (d * 0.82))
    if loss is None or loss < 0:
        x, y = path(u, 900, 548)
        spacecraft(img, cam, x, y, 0.42, math.radians(-20), flame=0.0, t=t)
    if loss is not None and loss >= 0:
        for k in range(3):
            lt = loss - k * 0.9
            if lt > 0:
                rr = (lt * 520) % 780
                cv2c = cam.p(*path(1, 900, 548))
                gfx.polyline(img, [(cv2c[0] + rr * math.cos(a / 20 * 6.283), cv2c[1] + rr * math.sin(a / 20 * 6.283)) for a in range(21)], mixc((150, 170, 255), (30, 30, 70), rr / 780), 3)
        img[:] = (img.astype(np.float32) * (1 - 0.5 * ease(loss / 0.8))).astype(np.uint8)


@scene("verdict")
def verdict(img, ctx):
    t = ctx.t
    img[:] = gfx.gradient((24, 22, 56), (58, 34, 88))
    gfx.ambient(img, t, 50, 3)
    for i, (key, label, sub, col, y) in enumerate((("good", "MATH", "CORRECT", GREEN, 640), ("bad", "UNITS", "WRONG", REDC, 1080))):
        s = ctx.since(key)
        k = ease((s if s is not None else -1) / 0.3)
        if k <= 0:
            continue
        xo = (1 - k) * (-900 if i == 0 else 900)
        y = y + 12 * math.sin(t * 2.2 + i * 2.1)
        paper(img, rrect_pts(90 + xo, y - 170, W - 90 + xo, y + 170, 50), (40, 40, 92))
        circle(img, (250 + xo, y), 105, col)
        if i == 0:
            polyline(img, [(205 + xo, y + 5), (240 + xo, y + 45), (300 + xo, y - 40)], WHITE, 22)
        else:
            line(img, (205 + xo, y - 45), (295 + xo, y + 45), WHITE, 22); line(img, (295 + xo, y - 45), (205 + xo, y + 45), WHITE, 22)
        text(img, label, (700 + xo, y - 50), 96, WHITE)
        text(img, sub, (700 + xo, y + 60), 96, col)


@scene("units_compare")
def units_compare(img, ctx):
    cam, t = ctx.cam, ctx.t
    img[:] = gfx.gradient((16, 16, 42), (40, 24, 70))
    gfx.ambient(img, t, 46, 4)
    ox = 110
    ratio = 4.45
    for key, yy, col, lab, mult in (("a", 520, BLUE, "WHAT THE SOFTWARE READ", 1.0), ("b", 1000, ORANGE, "WHAT WAS ACTUALLY SENT", ratio)):
        s = ctx.since(key)
        k = ease((s if s is not None else -1) / 0.6)
        if k <= 0:
            continue
        L = 160 * mult * k
        paper(img, rrect_pts(ox, yy - 28, ox + L, yy + 28, 28), col)
        poly(img, [(ox + L - 6, yy - 62), (ox + L + 80, yy), (ox + L - 6, yy + 62)], col)
        if L > 60:
            sx = ox + ((t * 420 + (0 if key == "a" else 200)) % max(L, 1))
            poly(img, [(sx, yy - 22), (min(sx + 40, ox + L), yy - 22), (min(sx + 10, ox + L), yy + 22), (sx - 30, yy + 22)], mixc(col, (255, 255, 255), 0.55))
        text(img, lab, (ox, yy - 100), 36, (200, 205, 240), "SemiBold", anchor="l")
        text(img, f"{mult * k:.2f}×" if mult > 1 else "1×", (ox + 20, yy + 100), 70, col, anchor="l")
    s = ctx.since("ratio")
    if s is not None and s > 0:
        k = ease(s / 0.4)
        yb = 1360 + 9 * math.sin(t * 2.4)
        paper(img, rrect_pts(W / 2 - 340 * k, yb - 70 * k, W / 2 + 340 * k, yb + 70 * k, 36), (40, 40, 100))
        text(img, "1 lbf = 4.45 N", (W / 2, yb), 78 * k, WHITE)


@scene("burnup")
def burnup(img, ctx):
    cam, t, d = ctx.cam, ctx.t, ctx.d
    u = clamp(t / d)
    img[:] = gfx.gradient((8, 8, 26), mixc((50, 20, 26), (130, 50, 28), u))
    rr = np.random.default_rng(5)
    glow(img, (W / 2, 1700), 1200, (255, 130, 60), 0.45)
    x = lerp(-400, 240, ease(u * 1.1)); y = lerp(-620, 420, ease(u * 1.1))
    for i in range(18):
        a = clamp(u * 1.0 - i * 0.02)
        glow(img, cam.p(x - i * 28, y - i * 22), cam.r(120 - i * 5), (255, 200 - i * 6, 90), 0.8 * (1 - i / 18))
    circle(img, cam.p(x, y), cam.r(46 * (1 + 0.5 * ease((u - 0.2) / 0.5))), (255, 244, 200))
    gfx.polyline(img, [(W / 2 + 900 * math.cos(math.radians(a)), 2450 + 900 * math.sin(math.radians(a))) for a in range(200, 341, 5)], (255, 190, 120), 6)
    if u < 0.38:
        spacecraft(img, cam, x, y, 0.55, 0.7, flame=0.0, t=t)
    else:
        b = (u - 0.38) / 0.62
        for i in range(16):
            vx, vy, sp = rr.uniform(-340, 340), rr.uniform(-80, 360), rr.uniform(-6, 6)
            px, py = x + vx * b * 2.0, y + vy * b * 2.0 + 200 * b * b
            col = mixc((255, 220, 120), (120, 60, 40), b)
            s = 46 * (1 - 0.6 * b) * (1 + (i % 3) * 0.6)
            a = sp * b
            paper(img, cam.pts([(px + s * math.cos(a + k * 1.6), py + s * math.sin(a + k * 1.6)) for k in range(4)]), col, off=(4, 6))
            glow(img, cam.p(px, py), cam.r(110 * (1 - b)), (255, 170, 70), 0.7 * (1 - b))
    img[:] = (img.astype(np.float32) * (1 - 0.6 * ease((u - 0.8) / 0.2))).astype(np.uint8)


@scene("twist_stamp")
def twist_stamp(img, ctx):
    t = ctx.t
    img[:] = gfx.gradient((22, 18, 52), (62, 32, 92))
    cam = ctx.cam
    k = ease(t / 0.4)
    q = ctx.since("q"); st = ctx.since("stamp")
    gfx.ambient(img, t, 46, 5)
    text(img, "100", (400, 800), 300 * k * (1 + 0.02 * math.sin(t * 3)), WHITE, alpha=k)
    if q is not None and q > 0 and (st is None or st < 0):
        text(img, "100 … what?", (W / 2, 1030), 76, (200, 190, 255), "SemiBold", alpha=ease(q / 0.3))
        wob = math.sin(q * 14) * 6
        text(img, "?", (800, 790 + wob), 200, ORANGE)
    if st is not None and st > 0:
        s = ease(st / 0.12); sc = lerp(2.4, 1.0, s)
        a = clamp(st / 0.1)
        w, h = 300 * sc, 150 * sc
        c = (830, 800)
        paper(img, rrect_pts(c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2, 30 * sc), GREEN, off=(8, 12))
        text(img, "N·s", c, 100 * sc, INK, alpha=a)
        for kk in range(3):
            ring = ((st - kk * 0.55) % 1.65) / 1.65
            if st - kk * 0.55 < 0: continue
            gfx.polyline(img, [(c[0] + 520 * ring * math.cos(i / 24 * 6.283), c[1] + 520 * ring * math.sin(i / 24 * 6.283)) for i in range(25)], mixc((255, 255, 255), (60, 40, 90), ring), max(2, int(10 * (1 - ring))))
        rr = np.random.default_rng(9)
        for i in range(36):
            x0, vy, sp, hue = rr.uniform(60, W - 60), rr.uniform(220, 520), rr.uniform(-5, 5), i % 4
            yy = -40 + (st - 0.15) * vy
            if st < 0.15 or yy > H + 40: continue
            cc = ((255, 214, 0), (80, 210, 255), (255, 90, 170), (120, 240, 160))[hue]
            a = sp * st; sz = 16
            poly(img, [(x0 + 30 * math.sin(st * 2 + i) + sz * math.cos(a + k * 1.57), yy + sz * math.sin(a + k * 1.57)) for k in range(4)], cc)
        text(img, "CHECK THE UNIT.", (W / 2, 1220), 70, WHITE, alpha=ease((st - 0.4) / 0.3))


class Ctx:
    def __init__(self, t, d, fps, cam, params, cues, mood_fn=None):
        self.t, self.d, self.fps, self.cam, self.p, self._cues, self._mood = t, d, fps, cam, params, cues, mood_fn

    def since(self, name):
        c = self._cues.get(name)
        return None if c is None else self.t - c

    def mood(self, side, t):
        return self._mood(side, t) if self._mood else "neutral"
