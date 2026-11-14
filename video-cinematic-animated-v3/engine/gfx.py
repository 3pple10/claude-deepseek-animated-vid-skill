"""gfx.py - our own 2.5D vector drawing + camera core (OpenCV/NumPy). Original code."""
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SH = 4                      # sub-pixel bits
FD = "/usr/share/fonts/opentype/inter/"


def _p(pts):
    return (np.asarray(pts, dtype=np.float64) * (1 << SH)).round().astype(np.int32)


def poly(img, pts, col):
    cv2.fillPoly(img, [_p(pts)], col, cv2.LINE_AA, SH)


def circle(img, c, r, col):
    if r < 0.3:
        return
    cv2.circle(img, (int(round(c[0] * 16)), int(round(c[1] * 16))), int(round(r * 16)), col, -1, cv2.LINE_AA, 4)


def line(img, a, b, col, w=3):
    cv2.line(img, (int(a[0] * 16), int(a[1] * 16)), (int(b[0] * 16), int(b[1] * 16)), col, max(1, int(round(w))), cv2.LINE_AA, 4)


def polyline(img, pts, col, w=3, closed=False):
    cv2.polylines(img, [_p(pts)], closed, col, max(1, int(round(w))), cv2.LINE_AA, SH)


def rrect_pts(x0, y0, x1, y1, r, seg=6):
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rrect(img, x0, y0, x1, y1, r, col):
    poly(img, rrect_pts(x0, y0, x1, y1, r), col)


def paper(img, pts, col, off=(5, 9), shade=0.35):
    """cut-paper look: soft offset shadow, then the shape."""
    sh = tuple(int(c * (1 - shade)) for c in col)
    poly(img, [(x + off[0], y + off[1]) for x, y in pts], sh)
    poly(img, pts, col)


_glow_cache = {}
def glow(img, c, r, col, alpha=0.6):
    r = int(r)
    if r < 2 or alpha <= 0:
        return
    key = min(r, 900) // 4
    if key not in _glow_cache:
        rr = key * 4 + 4
        yy, xx = np.mgrid[-rr:rr + 1, -rr:rr + 1]
        d = np.sqrt(xx ** 2 + yy ** 2) / rr
        _glow_cache[key] = np.clip(1 - d, 0, 1) ** 2.0
    m = _glow_cache[key]
    rr = (m.shape[0] - 1) // 2
    sc = r / rr
    if abs(sc - 1) > 0.02:
        m = cv2.resize(m, (int(m.shape[1] * sc) | 1, int(m.shape[0] * sc) | 1))
    h, w = m.shape
    cx, cy = int(c[0]), int(c[1])
    x0, y0 = cx - w // 2, cy - h // 2
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    mm = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None] * alpha
    roi = img[Y0:Y1, X0:X1].astype(np.float32)
    img[Y0:Y1, X0:X1] = np.clip(roi * (1 - mm) + np.array(col, np.float32) * mm, 0, 255).astype(np.uint8)


def clip_circle(img, c, r, fn):
    """run fn(tmp_img) on a copy and keep only the part inside the circle (for shaded planets)."""
    x0, y0 = int(max(0, c[0] - r - 2)), int(max(0, c[1] - r - 2))
    x1, y1 = int(min(W, c[0] + r + 2)), int(min(H, c[1] + r + 2))
    if x1 <= x0 or y1 <= y0:
        return
    tmp = img.copy()
    fn(tmp)
    mask = np.zeros((H, W), np.uint8)
    cv2.circle(mask, (int(round(c[0] * 16)), int(round(c[1] * 16))), int(round(r * 16)), 255, -1, cv2.LINE_AA, 4)
    m = mask[y0:y1, x0:x1, None].astype(np.float32) / 255
    img[y0:y1, x0:x1] = (tmp[y0:y1, x0:x1] * m + img[y0:y1, x0:x1] * (1 - m)).astype(np.uint8)


_grad_cache = {}
def gradient(top, bot):
    key = (tuple(top), tuple(bot))
    if key not in _grad_cache:
        t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        g = np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t
        _grad_cache[key] = np.repeat(g, W, axis=1).astype(np.uint8)
        if len(_grad_cache) > 80:
            _grad_cache.pop(next(iter(_grad_cache)))
    return _grad_cache[key].copy()


_text_cache = {}
def text(img, s, c, size, col, weight="Bold", alpha=1.0, angle=0.0, anchor="c"):
    """centered text sprite (cached), blended with alpha."""
    size = max(6, int(round(size)))
    key = (s, size, weight)
    if key not in _text_cache:
        f = ImageFont.truetype(FD + f"InterDisplay-{weight}.otf" if weight in ("Bold", "SemiBold") else FD + f"Inter-{weight}.otf", size)
        l, t, r, b = f.getbbox(s)
        im = Image.new("L", (r - l + 8, b - t + 8), 0)
        ImageDraw.Draw(im).text((4 - l, 4 - t), s, font=f, fill=255)
        _text_cache[key] = np.array(im)
        if len(_text_cache) > 400:
            _text_cache.pop(next(iter(_text_cache)))
    m = _text_cache[key]
    if angle:
        M = cv2.getRotationMatrix2D((m.shape[1] / 2, m.shape[0] / 2), -angle, 1.0)
        m = cv2.warpAffine(m, M, (m.shape[1], m.shape[0]))
    h, w = m.shape
    x0 = int(c[0] - (0 if anchor == "l" else w / 2)); y0 = int(c[1] - h / 2)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    mm = (m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None].astype(np.float32) / 255) * alpha
    roi = img[Y0:Y1, X0:X1].astype(np.float32)
    img[Y0:Y1, X0:X1] = (roi * (1 - mm) + np.array(col, np.float32) * mm).astype(np.uint8)


def text_w(s, size, weight="Bold"):
    f = ImageFont.truetype(FD + f"InterDisplay-{weight}.otf" if weight in ("Bold", "SemiBold") else FD + f"Inter-{weight}.otf", int(size))
    return f.getlength(s)


class Cam:
    """2.5D camera: depth 0 = screen-locked, 1 = world plane, <1 = far (parallax)."""
    def __init__(self, x=0.0, y=0.0, zoom=1.0, roll=0.0, sx=0.0, sy=0.0):
        self.x, self.y, self.zoom, self.roll, self.sx, self.sy = x, y, zoom, roll, sx, sy

    def p(self, wx, wy, depth=1.0):
        dx = (wx - self.x * depth) * self.zoom
        dy = (wy - self.y * depth) * self.zoom
        c, s = math.cos(self.roll), math.sin(self.roll)
        return (W / 2 + dx * c - dy * s + self.sx, H / 2 + dx * s + dy * c + self.sy)

    def pts(self, pts, depth=1.0):
        return [self.p(x, y, depth) for x, y in pts]

    def r(self, v):
        return v * self.zoom


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def lerp(a, b, k):
    return a + (b - a) * k


def mixc(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


_amb = {}
def ambient(img, t, n=44, seed=1, col=(200, 212, 255), speed=60.0, alpha=0.6):
    """drifting light motes (screen space): keeps any scene alive without changing its layout."""
    if (seed, n) not in _amb:
        r = np.random.default_rng(seed)
        _amb[(seed, n)] = np.c_[r.uniform(0, W, n), r.uniform(0, H, n), r.uniform(0.5, 1.6, n), r.uniform(0, 6.28, n), r.uniform(3, 9, n)]
    for x0, y0, sp, ph, rad in _amb[(seed, n)]:
        x = (x0 + 14 * math.sin(t * 0.8 + ph)) % W
        y = (y0 - speed * sp * t) % H
        glow(img, (x, y), rad * 3.2, col, alpha * (0.55 + 0.45 * math.sin(t * 2 + ph)))
