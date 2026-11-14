"""scenes_csv.py - scenes for CSV / spreadsheet-agent product shorts. Original code, same cut-paper style as scenes.py.
Scenes: csv_drop, prompt_box, agent_build, device_local, audit_table, more_burst, compare_tabs, free_tokens.
Every scene is fn(img, ctx), deterministic, and renders with empty params and no cues."""
import math
import numpy as np
from . import gfx
from .gfx import poly, circle, line, polyline, paper, glow, rrect_pts, ease, clamp, lerp, mixc
from .scenes import scene

BG_T, BG_B = (9, 13, 33), (30, 22, 72)
CARD, CARD2, CELL = (30, 38, 86), (42, 52, 112), (36, 46, 100)
MINT, CYAN, AMBER, CORAL, VIOLET = (72, 224, 172), (92, 200, 255), (255, 190, 82), (255, 102, 114), (162, 132, 255)
WHITE, MUTED, INK, BAR = (245, 246, 250), (150, 164, 208), (20, 22, 46), (96, 110, 168)
PANEL = (22, 30, 70)


# ------------------------------------------------------------------ helpers
def since(ctx, n):
    v = ctx.since(n)
    return -9.0 if v is None else v


def pop(s):
    """spring 0 -> 1 with a small overshoot; 0 before the cue."""
    return 0.0 if s <= 0 else 1 - math.exp(-s * 13) * math.cos(s * 22)


def bg(img, t, seed=2, top=BG_T, bot=BG_B):
    img[:] = gfx.gradient(top, bot)
    gfx.ambient(img, t, 36, seed, col=(150, 180, 255), speed=45, alpha=0.5)


def T(img, cam, s, x, y, size, col=WHITE, weight="Bold", alpha=1.0, anchor="c", depth=1.0):
    if alpha > 0.02:
        gfx.text(img, s, cam.p(x, y, depth), size * cam.zoom, col, weight, alpha, math.degrees(cam.roll), anchor)


def rot(pts, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def card(img, cam, x0, y0, x1, y1, r, col, ang=0.0, depth=1.0, off=(6, 10), shade=0.45):
    pts = rrect_pts(x0, y0, x1, y1, r)
    if ang:
        pts = rot(pts, ((x0 + x1) / 2, (y0 + y1) / 2), ang)
    paper(img, cam.pts(pts, depth), col, off=(off[0] * cam.zoom, off[1] * cam.zoom), shade=shade)


def flat(img, cam, x0, y0, x1, y1, r, col, depth=1.0):
    poly(img, cam.pts(rrect_pts(x0, y0, x1, y1, r), depth), col)


def pill(img, cam, cx, cy, w, h, col, k=1.0, **kw):
    if k > 0.02:
        card(img, cam, cx - w * k / 2, cy - h * k / 2, cx + w * k / 2, cy + h * k / 2, h * k / 2, col, **kw)


def check(img, cam, cx, cy, s, col, w=14):
    polyline(img, cam.pts([(cx - 0.5 * s, cy + 0.02 * s), (cx - 0.12 * s, cy + 0.4 * s), (cx + 0.52 * s, cy - 0.36 * s)]), col, max(2, w * cam.zoom))


def arc(img, cam, cx, cy, r, a0, a1, col, w, n=28):
    polyline(img, cam.pts([(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]), col, max(2, w * cam.zoom))


def ring(img, cam, c, r, col, w):
    polyline(img, cam.pts([(c[0] + r * math.cos(i / 40 * 6.2832), c[1] + r * math.sin(i / 40 * 6.2832)) for i in range(40)]), col, max(1, w * cam.zoom), closed=True)


def dashed(img, pts, col, w, dash=34, gap=22, phase=0.0):
    P = np.array(list(pts) + [pts[0]], float)
    seg = np.hypot(*(P[1:] - P[:-1]).T)
    cum = np.r_[0, np.cumsum(seg)]
    n = max(2, int(cum[-1] / 5))
    d = np.linspace(0, cum[-1], n)
    X, Y = np.interp(d, cum, P[:, 0]), np.interp(d, cum, P[:, 1])
    on = ((d + phase) % (dash + gap)) < dash
    for i in range(n - 1):
        if on[i] and on[i + 1]:
            line(img, (X[i], Y[i]), (X[i + 1], Y[i + 1]), col, w)


def star4(img, cam, cx, cy, r, col):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    poly(img, cam.pts(pts), col)


# ================================================================ 1. csv_drop
def file_card(img, cam, cx, cy, ang, kind):
    w, h = 270, 350
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    hc = MINT if kind == "csv" else (52, 178, 108)
    R = lambda pts: cam.pts(rot(pts, (cx, cy), ang))
    paper(img, R(rrect_pts(x0, y0, x1, y1, 28)), (238, 242, 252), off=(7 * cam.zoom, 11 * cam.zoom))
    band = 92
    poly(img, R(rrect_pts(x0, y0, x1, y0 + band, 28)), hc)
    poly(img, R([(x0, y0 + band * 0.5), (x1, y0 + band * 0.5), (x1, y0 + band), (x0, y0 + band)]), hc)
    p = cam.p(*rot([(cx, y0 + band * 0.5)], (cx, cy), ang)[0])
    gfx.text(img, ".CSV" if kind == "csv" else ".XLSX", p, 56 * cam.zoom, WHITE, "Bold", 1.0, math.degrees(cam.roll + ang))
    for i in range(5):
        yy = y0 + band + 44 + i * 46
        if kind == "csv":
            poly(img, R(rrect_pts(x0 + 30, yy - 10, x0 + 30 + (w - 60) * (0.78, 0.56, 0.68, 0.46, 0.62)[i], yy + 10, 10)), (196, 206, 232))
        else:
            cw = (w - 56) / 3
            for j in range(3):
                xx = x0 + 28 + j * cw
                poly(img, R(rrect_pts(xx + 3, yy - 15, xx + cw - 3, yy + 15, 6)), (196, 232, 210) if (i + j) % 2 == 0 else (172, 218, 192))


@scene("csv_drop")
def csv_drop(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 2)
    sc, sx, sd = since(ctx, "csv"), since(ctx, "excel"), since(ctx, "done")
    dk = ease(sd / 0.3)
    zc = mixc(CYAN, MINT, dk)
    T(img, cam, "DROP YOUR FILE", 0, -560, 68, MUTED, "SemiBold", alpha=ease(t / 0.5), depth=0.9)
    glow(img, cam.p(0, 60), 640 * cam.zoom, zc, 0.10 + 0.14 * dk)
    card(img, cam, -410, -370, 410, 490, 70, PANEL, shade=0.5)
    dashed(img, cam.pts(rrect_pts(-388, -348, 388, 468, 54, 8)), zc, max(3, 6 * cam.zoom), phase=t * 56 * (1 - dk))
    ic = 1 - clamp((sc + 0.35) / 0.3)
    if ic > 0.02:
        by = 12 * math.sin(t * 3.2)
        col = mixc(PANEL, CYAN, 0.85 * ic)
        poly(img, cam.pts([(-76, 20 + by), (76, 20 + by), (0, -76 + by)]), col)
        poly(img, cam.pts(rrect_pts(-26, 10 + by, 26, 120 + by, 8)), col)
    for s, lx, ly, a0, kind in ((sc, -170, 130, -0.10, "csv"), (sx, 175, 160, 0.09, "xlsx")):
        if s < -0.6:
            continue
        u = clamp((s + 0.55) / 0.55)
        y = lerp(-1300, ly, u * u)
        if s > 0:
            y -= 26 * math.exp(-s * 5.5) * abs(math.sin(s * 15))
        file_card(img, cam, lx, y, a0 + (1 - u) * 0.45 * (1 if lx < 0 else -1), kind)
        if 0 < s < 0.55:
            ring(img, cam, (lx, ly + 150), lerp(30, 230, s / 0.55), mixc(CYAN, PANEL, s / 0.55), 6 * (1 - s / 0.55) + 1)
    if sd > -0.05:
        k = pop(sd)
        circle(img, cam.p(0, -212), 86 * k * cam.zoom, (36, 130, 98))
        circle(img, cam.p(0, -222), 86 * k * cam.zoom, MINT)
        if k > 0.6:
            check(img, cam, 0, -222, 90 * k, WHITE, 16)
        T(img, cam, "READY", 0, -100, 56, MINT, alpha=ease((sd - 0.1) / 0.25))
        for i in range(2):
            r = ((sd - i * 0.35) % 1.4) / 1.4
            if sd - i * 0.35 > 0:
                ring(img, cam, (0, -222), 90 + 260 * r, mixc(MINT, PANEL, r), 7 * (1 - r))


# ================================================================ 2. prompt_box
_rr = np.random.default_rng(5)
_PB_W, _PB_J = _rr.uniform(0.35, 0.8, (6, 4)), _rr.uniform(-1, 1, (6, 4))
_PB_GROUPS = {"c1": [(1, 0), (2, 2), (4, 1)], "c2": [(1, 3), (3, 0), (5, 2)], "c3": [(2, 1), (3, 3), (5, 0)]}
_PB_FLAG = {rc: g for g, cells in _PB_GROUPS.items() for rc in cells}


@scene("prompt_box")
def prompt_box(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 4)
    T(img, cam, "TELL US WHAT YOU WANT", 0, -700, 54, MUTED, "SemiBold", alpha=ease(t / 0.4), depth=0.9)
    card(img, cam, -450, -620, 450, -330, 56, CARD)
    full = "Clean up my messy sheet"
    n = int(max(0.0, t - 0.35) * 15)
    typed = full[:min(n, len(full))]
    caret = (int(t * 2.5) % 2 == 0) or n < len(full)
    T(img, cam, typed + ("|" if caret else ""), -395, -475, 54, WHITE, "Medium", anchor="l")
    s3 = since(ctx, "c3")
    pk = 1 + 0.12 * math.exp(-max(s3, 0) * 6) * (1 if s3 > 0 else 0)
    circle(img, cam.p(365, -465), 58 * pk * cam.zoom, (36, 130, 98))
    circle(img, cam.p(365, -475), 58 * pk * cam.zoom, MINT)
    polyline(img, cam.pts([(341, -468), (365, -494), (389, -468)]), INK, max(2, 9 * cam.zoom))
    line(img, cam.p(365, -494), cam.p(365, -450), INK, max(2, 9 * cam.zoom))
    for cue, label, col, cx in (("c1", "CLEAN", MINT, -300), ("c2", "EDIT", CYAN, 0), ("c3", "FIX", AMBER, 300)):
        flat(img, cam, cx - 135, -235, cx + 135, -105, 65, (26, 34, 78))
        k = pop(since(ctx, cue))
        pill(img, cam, cx, -170, 270, 130, col, k=k)
        T(img, cam, label, cx, -170, 52 * min(k, 1.1), INK, "Bold", alpha=clamp(k))
    dy = (1 - ease(t / 0.6)) * 200
    for r in range(6):
        for c in range(4):
            x0, x1 = -440 + c * 220 + 6, -440 + c * 220 + 214
            y0 = 10 + r * 110 + 6 + dy
            y1 = y0 + 98
            hdr = r == 0
            g = _PB_FLAG.get((r, c))
            fk = ease(since(ctx, g) / 0.4) if g else 0.0
            flat(img, cam, x0, y0, x1, y1, 16, (48, 58, 124) if hdr else CELL)
            if g:
                polyline(img, cam.pts(rrect_pts(x0, y0, x1, y1, 16), 1.0), mixc(CORAL, MINT, fk), max(2, 4 * cam.zoom), closed=True)
                if fk < 0.95:
                    circle(img, cam.p(x1 - 24, y0 + 24), 12 * (1 - fk) * cam.zoom, CORAL)
            bw = (x1 - x0 - 44) * _PB_W[r, c]
            off = _PB_J[r, c] * 26 * (1 - fk) if g else 0
            bc = mixc(CORAL, MINT, fk) if g else ((150, 162, 220) if hdr else BAR)
            flat(img, cam, x0 + 22 + off, y0 + 38, x0 + 22 + off + bw, y0 + 60, 11, bc)


# ================================================================ 3. agent_build
STEPS = ("Read your file", "Find the issues", "Write the transform", "Apply and verify", "Export clean data")


def robot(img, cam, cx, cy, t, look=(0, 1), bright=0.0):
    glow(img, cam.p(cx, cy), 360 * cam.zoom, VIOLET, 0.30 + 0.30 * bright)
    dashed(img, cam.pts([(cx + 235 * math.cos(i / 48 * 6.2832), cy + 235 * math.sin(i / 48 * 6.2832)) for i in range(48)]), VIOLET, max(3, 5 * cam.zoom), phase=t * 90)
    card(img, cam, cx - 150, cy - 120, cx + 150, cy + 120, 70, (222, 226, 252), off=(8, 12))
    for sx in (-1, 1):
        circle(img, cam.p(cx + sx * 168, cy), 28 * cam.zoom, (140, 150, 215))
    flat(img, cam, cx - 118, cy - 70, cx + 118, cy + 70, 46, (22, 24, 58))
    ph = t % 2.6
    eh = 1 - 0.9 * math.sin(ph / 0.14 * math.pi) if ph < 0.14 else 1.0
    for sx in (-1, 1):
        ex, ey = cx + sx * 52 + look[0] * 8, cy + look[1] * 6
        flat(img, cam, ex - 23, ey - 27 * eh, ex + 23, ey + 27 * eh, 14, MINT)
    line(img, cam.p(cx, cy - 120), cam.p(cx, cy - 190), (140, 150, 210), max(3, 10 * cam.zoom))
    pulse = 0.6 + 0.4 * math.sin(t * 6)
    glow(img, cam.p(cx, cy - 196), 70 * cam.zoom, AMBER, 0.5 * pulse)
    circle(img, cam.p(cx, cy - 196), 19 * cam.zoom, AMBER)


@scene("agent_build")
def agent_build(img, ctx):
    cam, t, d = ctx.cam, ctx.t, ctx.d
    bg(img, t, 7)
    sb, sd = since(ctx, "build"), since(ctx, "done")
    robot(img, cam, 0, -560, t, bright=(1 - clamp(sb / 0.6)) if sb > 0 else 0.0)
    card(img, cam, -460, -230, 460, 660, 44, (16, 20, 52))
    flat(img, cam, -460, -230, 460, -130, 44, (30, 36, 84))
    flat(img, cam, -460, -180, 460, -130, 0, (30, 36, 84))
    for i, c in enumerate((CORAL, AMBER, MINT)):
        circle(img, cam.p(-405 + i * 44, -180), 14 * cam.zoom, c)
    T(img, cam, "agent  /  build", 40, -180, 34, MUTED, "SemiBold")
    sp = max(0.35, (d - 1.2) / 5)
    for i, label in enumerate(STEPS):
        ta = 0.35 + i * sp
        tb = ta + sp
        y = -62 + i * 112
        state = 2 if t >= tb else (1 if t >= ta else 0)
        if state == 1:
            flat(img, cam, -436, y - 46, 436, y + 46, 22, (36, 46, 104))
        cx = -375
        if state == 2:
            circle(img, cam.p(cx, y), 32 * cam.zoom, MINT)
            check(img, cam, cx, y, 38, INK, 8)
        elif state == 1:
            ring(img, cam, (cx, y), 30, (52, 64, 128), 6)
            arc(img, cam, cx, y, 30, t * 7, t * 7 + 4.0, CYAN, 8)
        else:
            ring(img, cam, (cx, y), 28, (52, 64, 128), 5)
        T(img, cam, label, -318, y, 48, WHITE if state else (104, 116, 166), "Medium", anchor="l")
    f = clamp((t - 0.35) / (5 * sp))
    flat(img, cam, -400, 575, 400, 615, 20, (30, 36, 84))
    if f > 0.02:
        flat(img, cam, -400, 575, -400 + 800 * f, 615, 20, mixc(CYAN, MINT, f))
    T(img, cam, f"{int(f * 100)}%", 340, 535, 38, MUTED, "SemiBold")
    if sd > 0:
        k = pop(sd)
        pill(img, cam, 0, 810, 640, 124, MINT, k=k)
        if k > 0.5:
            check(img, cam, -235, 810, 44, INK, 10)
            T(img, cam, "BUILD COMPLETE", 40, 810, 46 * min(k, 1.1), INK)


# ================================================================ 4. device_local
def loop_icon(img, cam, cx, cy, r, a0, col):
    a1 = a0 + 4.8
    arc(img, cam, cx, cy, r, a0, a1, col, 9)
    ex, ey = cx + r * math.cos(a1), cy + r * math.sin(a1)
    tx, ty = -math.sin(a1), math.cos(a1)
    px, py = math.cos(a1), math.sin(a1)
    poly(img, cam.pts([(ex + tx * 20, ey + ty * 20), (ex + px * 15, ey + py * 15), (ex - px * 15, ey - py * 15)]), col)


def pencil_icon(img, cam, cx, cy, col):
    line(img, cam.p(cx - 22, cy + 22), cam.p(cx + 20, cy - 20), col, max(3, 18 * cam.zoom))
    poly(img, cam.pts([(cx - 36, cy + 36), (cx - 34, cy + 10), (cx - 10, cy + 34)]), col)


@scene("device_local")
def device_local(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 9)
    sr, su, sn, sd = since(ctx, "r"), since(ctx, "u"), since(ctx, "run"), since(ctx, "dev")
    for s, y, label, col, kind in ((sr, -560, "REUSABLE", MINT, "loop"), (su, -410, "UPDATABLE", CYAN, "pencil")):
        k = pop(s)
        pill(img, cam, 0, y, 660, 124, col, k=k)
        if k > 0.5:
            if kind == "loop":
                loop_icon(img, cam, -225, y, 34, t * 4, INK)
            else:
                pencil_icon(img, cam, -225, y, INK)
            T(img, cam, label, 50, y, 58 * min(k, 1.1), INK)
    ly = 90
    card(img, cam, -430, ly - 300, 430, ly + 170, 40, (60, 70, 132), off=(8, 12))
    flat(img, cam, -404, ly - 274, 404, ly + 144, 22, (14, 18, 44))
    poly(img, cam.pts([(-470, ly + 170), (470, ly + 170), (430, ly + 232), (-430, ly + 232)]), (76, 86, 156))
    flat(img, cam, -70, ly + 170, 70, ly + 192, 10, (54, 62, 120))
    hl = int(t * 6) % 12
    for r in range(4):
        for c in range(3):
            x0, y0 = -360 + c * 240, ly - 240 + r * 94
            flat(img, cam, x0, y0, x0 + 224, y0 + 80, 12, (40, 50, 110) if r * 3 + c == hl else (26, 32, 74))
            flat(img, cam, x0 + 18, y0 + 28, x0 + 18 + 120 * (0.5 + 0.4 * ((r * 3 + c * 5) % 3) / 2), y0 + 50, 9, BAR)
    if sd > 0:
        k = pop(sd)
        glow(img, cam.p(0, ly - 30), 360 * cam.zoom, MINT, 0.35 * clamp(k))
        s = max(0.05, k)
        sh = [(-92 * s, -96 * s + ly - 30), (92 * s, -96 * s + ly - 30), (92 * s, 10 * s + ly - 30), (0, 116 * s + ly - 30), (-92 * s, 10 * s + ly - 30)]
        paper(img, cam.pts(sh), MINT, off=(7 * cam.zoom, 11 * cam.zoom))
        if k > 0.6:
            check(img, cam, 0, ly - 20, 100 * s, INK, 16)
        r = (sd % 1.2) / 1.2
        ring(img, cam, (0, ly - 30), 120 + 220 * r, mixc(MINT, (14, 18, 44), r), 6 * (1 - r) + 1)
    k = pop(sn)
    pill(img, cam, 0, 500, 800, 124, AMBER, k=k)
    T(img, cam, "RUNS ON YOUR DEVICE", 0, 500, 50 * min(k, 1.1), INK, alpha=clamp(k))


# ================================================================ 5. audit_table
_ar = np.random.default_rng(8)
_AT_W = _ar.uniform(0.35, 0.8, (8, 4))
_FLAGS = {(1, 1): CORAL, (2, 3): AMBER, (3, 0): AMBER, (5, 2): CORAL, (6, 1): VIOLET}


@scene("audit_table")
def audit_table(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 11)
    sa, se = since(ctx, "audit"), since(ctx, "engine")
    T(img, cam, "YOUR CLEAN DATA", 0, -700, 58, MUTED, "SemiBold", alpha=1 - clamp(sa / 0.12), depth=0.9)
    T(img, cam, "AUDIT ENGINE", 0, -700, 70, CYAN, "Bold", alpha=clamp((sa - 0.14) / 0.2), depth=0.9)
    top, rh, cw = -570, 104, 220
    ys = top + (1 - ease(t / 0.5)) * 140
    scan = ease(sa / 1.5) if sa > 0 else -1.0
    sy = ys + rh * 8 * scan
    for r in range(8):
        for c in range(4):
            x0, x1 = -440 + c * cw + 5, -440 + c * cw + cw - 5
            y0 = ys + r * rh + 5
            y1 = y0 + rh - 10
            passed = scan >= 0 and (ys + (r + 0.5) * rh) < sy
            f = _FLAGS.get((r, c))
            col = (48, 58, 124) if r == 0 else CELL
            if sa < 0 and r > 0 and r == 1 + int(t * 3.2) % 7:
                col = mixc(col, CYAN, 0.22)
            if passed and f:
                col = mixc(col, f, 0.5)
            flat(img, cam, x0, y0, x1, y1, 14, col)
            bw = (x1 - x0 - 40) * _AT_W[r, c]
            my = (y0 + y1) / 2
            flat(img, cam, x0 + 20, my - 10, x0 + 20 + bw, my + 10, 10, WHITE if (passed and f) else ((150, 162, 220) if r == 0 else BAR))
            if passed and f:
                pk = 1 + 0.18 * math.sin(t * 7 + r)
                circle(img, cam.p(x1 - 24, y0 + 24), 13 * pk * cam.zoom, f)
    if 0 <= scan:
        al = 1.0 if se < 0 else 1 - ease(se / 0.4)
        if al > 0.02 and scan < 1.0:
            glow(img, cam.p(0, sy), 420 * cam.zoom, CYAN, 0.28 * al)
            line(img, cam.p(-470, sy), cam.p(470, sy), mixc(PANEL, CYAN, al), max(3, 7 * cam.zoom))
    k = pop(se)
    if k > 0.02:
        card(img, cam, -440, 370, 440, 690, 44, (16, 20, 52))
        vals = (("CELLS CHECKED", 28, WHITE, -290), ("ISSUES FLAGGED", 5, CORAL, 0), ("CLEAN", 23, MINT, 290))
        cnt = ease(se / 0.8)
        for lab, v, col, x in vals:
            T(img, cam, str(int(round(v * cnt))), x, 490, 120 * min(k, 1.05), col)
            T(img, cam, lab, x, 600, 28, MUTED, "SemiBold", alpha=clamp(k))


# ================================================================ 6. more_burst
@scene("more_burst")
def more_burst(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 13, (12, 10, 40), (44, 24, 84))
    sm = since(ctx, "more")
    k = pop(sm)
    s0 = (0.45 + 0.55 * k) * (1 + 0.03 * math.sin(t * 4))
    for i in range(3):
        r = ((t * 0.7 - i * 0.33) % 1.0)
        ring(img, cam, (0, -140), 230 + 300 * r, mixc(MINT, (20, 16, 56), r), 5 * (1 - r) + 1)
    glow(img, cam.p(0, -140), 520 * cam.zoom, MINT, 0.22 + 0.2 * clamp(k))
    circle(img, cam.p(8, -128), 230 * s0 * cam.zoom, (14, 14, 44))
    circle(img, cam.p(0, -140), 230 * s0 * cam.zoom, CARD)
    flat(img, cam, -34 * s0, -150 * s0 - 140, 34 * s0, 150 * s0 - 140, 14, MINT)
    flat(img, cam, -150 * s0, -34 * s0 - 140, 150 * s0, 34 * s0 - 140, 14, MINT)
    T(img, cam, "AND THERE'S", 0, -500, 70, MUTED, "SemiBold", alpha=ease(t / 0.4))
    if sm > 0:
        for i in range(16):
            a = i / 16 * 6.2832 + 0.2
            u = clamp(sm / 0.6)
            r0, r1 = 260 + 380 * u, 300 + 520 * u
            line(img, cam.p(r0 * math.cos(a), -140 + r0 * math.sin(a)), cam.p(r1 * math.cos(a), -140 + r1 * math.sin(a)), mixc(MINT, (20, 16, 56), u), max(2, 7 * (1 - u) * cam.zoom))
    T(img, cam, "MORE", 0, 250, 230 * min(k, 1.08), WHITE, alpha=clamp(k * 1.5))
    for i, (col, y) in enumerate(((CORAL, 520), (AMBER, 640), (CYAN, 760))):
        u = ease((sm - 0.15 - i * 0.12) / 0.4)
        if u <= 0:
            continue
        x = lerp(900, 0, u)
        card(img, cam, x - 280, y - 46, x + 280, y + 46, 40, CARD)
        circle(img, cam.p(x - 230, y), 17 * cam.zoom, col)
        flat(img, cam, x - 190, y - 12, x + 40, y + 12, 12, BAR)
        flat(img, cam, x + 60, y - 12, x + 210, y + 12, 12, (60, 72, 138))


# ================================================================ 7. compare_tabs
_cr = np.random.default_rng(21)
_CT_W = _cr.uniform(0.35, 0.85, (8, 2))
_CT_DIFF = [(1, 0), (2, 1), (4, 0), (5, 1), (6, 0)]


@scene("compare_tabs")
def compare_tabs(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 15)
    sc, sv, ss = since(ctx, "compare"), since(ctx, "visual"), since(ctx, "side")
    card(img, cam, -470, -770, 470, -630, 56, CARD)
    px = lerp(0, 300, ease(sc / 0.35))
    pill(img, cam, px, -700, 290, 100, CYAN)
    for lab, x in (("BUILD", -300), ("AUDIT", 0), ("COMPARE", 300)):
        T(img, cam, lab, x, -700, 40, INK if abs(px - x) < 140 else MUTED, "Bold")
    T(img, cam, "BEFORE", -255, -545, 46, CORAL, depth=0.95)
    T(img, cam, "AFTER", 255, -545, 46, MINT, depth=0.95)
    for x0, x1 in ((-470, -40), (40, 470)):
        card(img, cam, x0, -490, x1, 560, 36, PANEL)
    for side, (x0, x1) in enumerate(((-470, -40), (40, 470))):
        for r in range(8):
            for c in range(2):
                cx0 = x0 + 12 + c * 205
                y0 = -478 + r * 130 + 6
                lit = 0.0
                if (r, c) in _CT_DIFF:
                    lit = ease((sv - _CT_DIFF.index((r, c)) * 0.14) / 0.25)
                tint = CORAL if side == 0 else MINT
                flat(img, cam, cx0, y0, cx0 + 195, y0 + 108, 14, mixc(CELL, tint, 0.38 * lit))
                bw = 150 * _CT_W[r, c]
                off = (_CT_W[r, c] - 0.6) * 40 * lit if side == 0 else 0
                bc = mixc(BAR, tint, lit)
                flat(img, cam, cx0 + 22 + off, y0 + 42, cx0 + 22 + off + (bw if side == 0 else 150 * 0.6), y0 + 66, 11, bc)
    for j, (r, c) in enumerate(_CT_DIFF):
        lit = ease((sv - j * 0.14) / 0.25)
        if lit > 0.02:
            y = -478 + r * 130 + 60
            col = mixc(PANEL, MINT, lit)
            line(img, cam.p(-34, y), cam.p(26, y), col, max(2, 6 * cam.zoom))
            poly(img, cam.pts([(34, y), (16, y - 14), (16, y + 14)]), col)
    line(img, cam.p(0, -490), cam.p(0, 560), CYAN, max(2, 5 * cam.zoom))
    hy = 35 + 10 * math.sin(t * 2.2)
    circle(img, cam.p(0, hy), 44 * cam.zoom, WHITE)
    poly(img, cam.pts([(-30, hy), (-12, hy - 13), (-12, hy + 13)]), INK)
    poly(img, cam.pts([(30, hy), (12, hy - 13), (12, hy + 13)]), INK)
    if ss > 0:
        r = (ss % 1.3) / 1.3
        ring(img, cam, (0, hy), 50 + 160 * r, mixc(CYAN, PANEL, r), 6 * (1 - r) + 1)
    k = pop(ss)
    pill(img, cam, 0, 760, 720, 110, CARD2, k=k)
    if k > 0.5:
        circle(img, cam.p(-290, 760), 16 * cam.zoom, MINT)
        T(img, cam, "5 CHANGES HIGHLIGHTED", 20, 760, 40 * min(k, 1.05), WHITE)


# ================================================================ 8. free_tokens
_fr = np.random.default_rng(33)
_FT_RAIN = np.c_[_fr.uniform(-480, 480, 16), _fr.uniform(0, 2200, 16), _fr.uniform(150, 330, 16), _fr.uniform(34, 70, 16), _fr.uniform(0, 6.28, 16)]
_FT_BURST = np.c_[_fr.uniform(-520, 520, 14), _fr.uniform(-1100, -300, 14), _fr.uniform(30, 52, 14), _fr.uniform(0, 6.28, 14)]


def coin(img, cam, cx, cy, r, spin, depth=1.0, glyph=True):
    w = max(0.14, abs(math.cos(spin)))
    n = 36
    ell = lambda rad, off=0.0: [(cx + rad * w * math.cos(2 * math.pi * i / n), cy + off + rad * math.sin(2 * math.pi * i / n)) for i in range(n)]
    poly(img, cam.pts(ell(r, r * 0.09), depth), (170, 108, 26))
    poly(img, cam.pts(ell(r), depth), (255, 200, 72))
    poly(img, cam.pts(ell(r * 0.82), depth), (255, 224, 124))
    poly(img, cam.pts(ell(r * 0.70), depth), (255, 196, 64))
    if glyph and w > 0.5:
        gfx.text(img, "T", cam.p(cx, cy, depth), r * 0.95 * cam.zoom, (150, 92, 16), "Bold", clamp((w - 0.5) / 0.4), math.degrees(cam.roll))


@scene("free_tokens")
def free_tokens(img, ctx):
    cam, t = ctx.cam, ctx.t
    bg(img, t, 17, (14, 12, 40), (50, 28, 72))
    sf, sa, st = since(ctx, "free"), since(ctx, "ads"), since(ctx, "tokens")
    for x, y0, sp, r, ph in _FT_RAIN:
        y = ((y0 + sp * t) % 2200) - 1100
        coin(img, cam, x, y, r * 0.8, t * 3 + ph, depth=0.8, glyph=False)
    glow(img, cam.p(0, -150), 600 * cam.zoom, AMBER, 0.28)
    coin(img, cam, 0, -150 + 14 * math.sin(t * 2.0), 250, t * 1.9)
    for i in range(6):
        a = i / 6 * 6.2832 + t * 0.5
        tw = 0.5 + 0.5 * math.sin(t * 4 + i * 1.7)
        star4(img, cam, 360 * math.cos(a), -150 + 300 * math.sin(a), 22 + 16 * tw, mixc((120, 100, 80), (255, 240, 190), tw))
    k = pop(sf)
    T(img, cam, "FREE", 0, -640, 270 * min(k, 1.08), AMBER, alpha=clamp(k * 1.5))
    ka = pop(sa)
    pill(img, cam, 0, 340, 800, 130, CARD2, k=ka)
    if ka > 0.5:
        card(img, cam, -355, 298, -265, 382, 14, WHITE, off=(4, 6))
        T(img, cam, "AD", -310, 340, 44, INK)
        T(img, cam, "AD-SUPPORTED", 0, 340, 50, WHITE)
        circle(img, cam.p(335, 340), 34 * cam.zoom, (255, 200, 72))
        T(img, cam, "T", 335, 340, 40, (150, 92, 16))
        for j in range(3):
            u = ((t * 0.9 + j / 3) % 1.0)
            circle(img, cam.p(lerp(-250, 290, u), 340), 7 * cam.zoom, mixc(PANEL, AMBER, math.sin(u * math.pi)))
    kt = pop(st)
    T(img, cam, "TOKENS", 0, 580, 160 * min(kt, 1.08), WHITE, alpha=clamp(kt * 1.5))
    if st > 0:
        for x, vy, r, ph in _FT_BURST:
            tt = st
            if tt < 2.4:
                coin(img, cam, x * tt * 0.6, -150 + vy * tt * 0.5 + 700 * tt * tt, r, tt * 9 + ph, glyph=False)
