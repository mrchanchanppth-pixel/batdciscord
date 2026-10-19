"""
premium_borders.py  -  10 premium avatar borders & glow effects (Pillow only, no numpy).

Drop this file next to main.py. main.py does:

    from premium_borders import PREMIUM_BORDERS, PREMIUM_SHAPES, draw_premium_ring
    AVATAR_BORDERS.update(PREMIUM_BORDERS)

and, inside its ring renderer:

    if info and info["shape"] in PREMIUM_SHAPES:
        draw_premium_ring(card, cx, cy, inner_r, thickness, info["shape"])

Run `python premium_borders.py` to render a preview sheet (premium_preview.png).

How the effects are built
  * conic (angular) gradients  - the colour sweeps AROUND the ring instead of top-to-bottom
  * bloom                      - a blurred copy of the ring's own colours sits under it (neon glow)
  * shape masks                - sparkles, petals, flames, feathers, crown ... drawn 2x supersampled
  * two-tone glow ("glow2")    - consumed by the profile-card code for a second halo colour
All sizes are expressed relative to `thickness`, so the rings scale with the card's SCALE factor.
"""
import colorsys
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

_SS = 2  # mask supersampling (smooth, anti-aliased edges)

# ---------------------------------------------------------------------------
# Shop dictionary entries (merge into AVATAR_BORDERS).  4,000,000 Coins or 30 AAA each.
#   start / end : accent colours - the whole profile card is themed from these
#   glow / glow2: halo colours behind the avatar (glow2 = optional second tone)
# ---------------------------------------------------------------------------
PREMIUM_BORDERS = {
    "ring6": {
        "name": "⚡ Cyberpunk Pulse", "shape": "cyberpunk",
        "start": (255, 45, 185, 255), "end": (0, 230, 255, 255),
        "glow": (255, 60, 190, 170), "glow2": (0, 220, 255, 150),
        "glow_blur": 24, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring7": {
        "name": "✨ Magical Stardust Trail", "shape": "stardust",
        "start": (214, 188, 255, 255), "end": (160, 140, 245, 255),
        "glow": (190, 160, 255, 160), "glow_blur": 26, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring8": {
        "name": "👑 Golden Regal Crest", "shape": "gold",
        "start": (255, 226, 120, 255), "end": (214, 150, 40, 255),
        "glow": (255, 200, 80, 175), "glow_blur": 20, "glow_spread": 14, "coins": 4_000_000, "aaa": 30,
    },
    "ring9": {
        "name": "🌸 Sakura Dream Drift", "shape": "sakura",
        "start": (255, 176, 210, 255), "end": (255, 120, 178, 255),
        "glow": (255, 150, 200, 160), "glow_blur": 26, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring10": {
        "name": "🌿 Emerald Aura Mist", "shape": "emerald",
        "start": (100, 255, 195, 255), "end": (10, 135, 95, 255),
        "glow": (40, 255, 165, 170), "glow_blur": 32, "glow_spread": 22, "coins": 4_000_000, "aaa": 30,
    },
    "ring11": {
        "name": "🔥 Crimson Inferno Flame", "shape": "inferno",
        "start": (255, 150, 40, 255), "end": (230, 40, 30, 255),
        "glow": (255, 80, 30, 190), "glow_blur": 24, "glow_spread": 22, "coins": 4_000_000, "aaa": 30,
    },
    "ring12": {
        "name": "🌌 Midnight Galaxy Shimmer", "shape": "galaxy",
        "start": (160, 130, 255, 255), "end": (80, 60, 200, 255),
        "glow": (110, 80, 255, 170), "glow_blur": 28, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring13": {
        "name": "🪽 Pure Feather Glow", "shape": "feather",
        "start": (255, 255, 255, 255), "end": (190, 205, 235, 255),
        "glow": (225, 232, 255, 160), "glow_blur": 26, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring14": {
        "name": "🌅 Sunset Vaporwave Aesthetic", "shape": "vaporwave",
        "start": (255, 80, 190, 255), "end": (0, 220, 255, 255),
        "glow": (255, 80, 190, 165), "glow2": (0, 220, 255, 140),
        "glow_blur": 24, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
    "ring15": {
        "name": "🌈 Rainbow Prism Loop", "shape": "rainbow",
        "start": (255, 115, 175, 255), "end": (110, 200, 255, 255),
        "glow": (190, 150, 255, 150), "glow_blur": 26, "glow_spread": 18, "coins": 4_000_000, "aaa": 30,
    },
}
PREMIUM_SHAPES = {info["shape"] for info in PREMIUM_BORDERS.values()}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
class _Mask:
    """An 'L' mask drawn at 2x and downsampled on get() for anti-aliased shapes."""

    def __init__(self, size):
        self.size = size
        self.mid = size / 2
        self.img = Image.new("L", (size * _SS, size * _SS), 0)
        self.d = ImageDraw.Draw(self.img)

    def _p(self, pts):
        return [(x * _SS, y * _SS) for x, y in pts]

    def circle(self, x, y, r, fill=255):
        self.d.ellipse(((x - r) * _SS, (y - r) * _SS, (x + r) * _SS, (y + r) * _SS), fill=fill)

    def ring(self, r_in, r_out, fill=255):
        self.circle(self.mid, self.mid, r_out, fill)
        self.circle(self.mid, self.mid, r_in, 0)

    def arc(self, r_in, r_out, a0, a1, fill=255):
        m = self.mid
        box = ((m - r_out) * _SS, (m - r_out) * _SS, (m + r_out) * _SS, (m + r_out) * _SS)
        self.d.pieslice(box, a0, a1, fill=fill)
        self.circle(m, m, r_in, 0)

    def poly(self, pts, fill=255):
        self.d.polygon(self._p(pts), fill=fill)

    def line(self, p0, p1, width, fill=255):
        self.d.line(self._p([p0, p1]), fill=fill, width=max(1, int(round(width * _SS))))

    def get(self):
        return self.img.resize((self.size, self.size), Image.Resampling.LANCZOS)


def _solid(mask, color, alpha=1.0):
    layer = Image.new("RGBA", mask.size, tuple(color[:3]) + (255,))
    layer.putalpha(mask if alpha >= 1 else mask.point(lambda v: int(v * alpha)))
    return layer


def _glow(mask, color, blur, strength=1.0):
    soft = mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * strength)))
    layer = Image.new("RGBA", mask.size, tuple(color[:3]) + (255,))
    layer.putalpha(soft)
    return layer


def _put(canvas, mask, color, blur=0, strength=1.0, alpha=1.0):
    """Composite a coloured shape, optionally with a soft neon bloom underneath."""
    if blur:
        canvas.alpha_composite(_glow(mask, color, blur, strength))
    canvas.alpha_composite(_solid(mask, color, alpha))


def _polar(cx, cy, radius, degrees):
    a = math.radians(degrees)
    return cx + radius * math.cos(a), cy + radius * math.sin(a)


def _grad_color(stops, t):
    """Sample a cyclic colour list (first == last) at t in [0,1)."""
    t %= 1.0
    n = len(stops) - 1
    x = t * n
    i = min(int(x), n - 1)
    f = x - i
    a, b = stops[i], stops[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


def _conic_rgb(size, stops, rotate=0.0, steps=360):
    wheel = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(wheel)
    mid = size / 2
    box = (mid - size, mid - size, mid + size, mid + size)
    for i in range(steps):
        a0 = rotate + i * 360 / steps
        d.pieslice(box, a0 - 0.4, a0 + 360 / steps + 0.4, fill=_grad_color(stops, (i + 0.5) / steps))
    return wheel


def _conic_layer(ring_mask, stops, rotate=0.0, bloom=0.0, bloom_strength=1.0):
    """RGBA layer: angular-gradient ring (+ colour-matched bloom underneath)."""
    size = ring_mask.size[0]
    wheel = _conic_rgb(size, stops, rotate)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if bloom:
        a = ring_mask.filter(ImageFilter.GaussianBlur(bloom)).point(lambda v: min(255, int(v * bloom_strength * 1.4)))
        glow = wheel.convert("RGBA")
        glow.putalpha(a)
        out.alpha_composite(glow)
    ring = wheel.convert("RGBA")
    ring.putalpha(ring_mask)
    out.alpha_composite(ring)
    return out


def _vgrad(size, stops, y0=0, y1=None):
    """Vertical multi-stop gradient (RGB), clamped outside [y0, y1]."""
    y1 = size - 1 if y1 is None else y1
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    n = len(stops) - 1
    for y in range(size):
        t = min(1.0, max(0.0, (y - y0) / max(1, (y1 - y0))))
        x = t * n
        i = min(int(x), n - 1)
        f = x - i
        a, b = stops[i], stops[i + 1]
        d.line((0, y, size, y), fill=tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3)))
    return img


def _xform(local, x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x + a * c - b * s, y + a * s + b * c) for a, b in local]


def _star_pts(x, y, r, inner=0.38, rot=-90):
    pts = []
    for i in range(8):
        rad = r if i % 2 == 0 else r * inner
        pts.append(_polar(x, y, rad, rot + i * 45))
    return pts


def _petal_pts(x, y, length, width, ang):
    """Cherry-blossom petal: narrow base, broad notched tip. (x, y) is the base point."""
    right, left = [], []
    n = 14
    for k in range(n + 1):
        s = k / n * 0.97
        if s <= 0.78:
            w = width * math.sin(math.pi / 2 * s / 0.78) ** 0.85
        else:
            w = width * math.cos((s - 0.78) / 0.22 * math.pi / 2) ** 0.55
        right.append((s * length, w))
        left.append((s * length, -w))
    return _xform(right + [(0.9 * length, 0)] + left[::-1], x, y, ang)


def _leaf_pts(x, y, length, width, ang, skew=0.0):
    right, left = [], []
    n = 12
    for k in range(n + 1):
        s = k / n
        w = width * math.sin(math.pi * s) ** 0.85
        right.append((s * length, w * (1 + skew)))
        left.append((s * length, -w * (1 - skew)))
    return _xform(right + left[::-1][1:], x, y, ang)


def _flame_pts(mid, r0, ang, length, half_w, curl):
    left, right = [], []
    n = 10
    for k in range(n + 1):
        s = k / n
        r = r0 + length * s
        w = half_w * (1 - s) ** 0.85 * (1 + 0.25 * math.sin(s * math.pi))
        c = ang + curl * s * s
        left.append(_polar(mid, mid, r, c - w))
        right.append(_polar(mid, mid, r, c + w))
    return left + right[::-1]


# ---------------------------------------------------------------------------
# The 10 renderers.  Each draws onto an RGBA canvas `L` centred on (size/2, size/2).
#   ri = radius where the ring starts, th = ring thickness, u = th / 8 (one "design unit")
# ---------------------------------------------------------------------------
def _r_cyberpunk(L, size, ri, th, u):
    """Layered neon pink/cyan tube ring + white-hot core + offset outer line + HUD brackets."""
    t = th + 2 * u
    ro = ri + t
    pink, cyan, violet = (255, 45, 185), (0, 230, 255), (140, 70, 255)
    stops = [pink, violet, cyan, violet, pink]

    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-40, bloom=7 * u))

    core = _Mask(size); core.ring(ri + t * 0.36, ri + t * 0.64)
    _put(L, core.get(), (255, 255, 255), alpha=0.55)

    outer = _Mask(size); outer.ring(ro + 4.5 * u, ro + 6.5 * u)
    L.alpha_composite(_conic_layer(outer.get(), stops, rotate=140, bloom=4 * u))

    for i, ang in enumerate((-45, 45, 135, 225)):
        b = _Mask(size); b.arc(ro + 10 * u, ro + 12.5 * u, ang - 13, ang + 13)
        _put(L, b.get(), cyan if i % 2 == 0 else pink, blur=3 * u, strength=1.3)
    pips = _Mask(size)
    for ang in (0, 90, 180, 270):
        x, y = _polar(size / 2, size / 2, ro + 11.2 * u, ang)
        pips.circle(x, y, 1.3 * u)
    _put(L, pips.get(), (255, 255, 255), blur=2 * u)


def _r_stardust(L, size, ri, th, u):
    """Soft pastel-purple ring with a trail of glowing stars and sparkles along the outer edge."""
    mid = size / 2
    ro = ri + th
    stops = [(206, 180, 255), (244, 224, 255), (172, 154, 250), (228, 204, 255), (206, 180, 255)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-20, bloom=6 * u, bloom_strength=0.8))
    hl = _Mask(size); hl.ring(ri + 1.2 * u, ri + 2.6 * u)
    _put(L, hl.get(), (255, 255, 255), alpha=0.45)

    palette = [(255, 255, 255), (255, 212, 244), (200, 235, 255), (255, 240, 190)]
    groups = [_Mask(size) for _ in palette]
    n = 30
    for k in range(n):                                   # tapering trail of particles
        t = k / (n - 1)
        r = ro + (5 + 9 * abs(math.sin(k * 1.9))) * u
        x, y = _polar(mid, mid, r, -75 + t * 260)
        s = (7.0 - 4.4 * t) * u
        if k % 3 == 0:
            groups[k % 4].poly(_star_pts(x, y, s * 1.25, 0.32))
        else:
            groups[k % 4].circle(x, y, s * 0.38)
    for i, ang in enumerate((-60, 40, 150, 250)):        # big twinkles with long arms
        x, y = _polar(mid, mid, ro + (14 + (i % 2) * 3) * u, ang)
        groups[i].poly(_star_pts(x, y, 8.4 * u, 0.2))
    for g, color in zip(groups, palette):
        _put(L, g.get(), color, blur=2.2 * u, strength=1.5)


def _r_gold(L, size, ri, th, u):
    """Metallic gold ring (banded conic gradient), pearl beading and a jewelled crown at the top."""
    mid = size / 2
    t = th + 2 * u
    ro = ri + t
    stops = [(255, 246, 176), (255, 214, 86), (168, 110, 24), (255, 228, 120),
             (110, 70, 12), (255, 238, 150), (255, 246, 176)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-60, bloom=6 * u, bloom_strength=0.9))
    dark = _Mask(size); dark.ring(ri, ri + 1 * u)
    _put(L, dark.get(), (95, 60, 8), alpha=0.6)
    light = _Mask(size); light.ring(ro - 1.1 * u, ro)
    _put(L, light.get(), (255, 250, 210), alpha=0.7)

    pearls = _Mask(size)
    for i in range(24):
        ang = i * 15 + 7.5
        if abs(((ang + 90 + 180) % 360) - 180) < 32:      # leave room for the crown
            continue
        x, y = _polar(mid, mid, ro + 3 * u, ang)
        pearls.circle(x, y, 1.5 * u)
    _put(L, pearls.get(), (255, 240, 190), blur=2 * u, strength=1.2)

    k = 1.4                                               # crown scale
    bx, by = mid, mid - (ro - 1 * u)                      # crown base centre (top of ring)
    pts = [(-18, 2), (-20, -12), (-10, -6), (0, -22), (10, -6), (20, -12), (18, 2)]
    crown_pts = [(bx + px * u * k, by + py * u * k) for px, py in pts]
    cm = _Mask(size); cm.poly(crown_pts); crown = cm.get()
    L.alpha_composite(_glow(crown, (255, 200, 70), 5 * u, 1.3))
    grad = _vgrad(size, [(255, 248, 190), (255, 210, 80), (170, 112, 26)],
                  int(by - 22 * u * k), int(by + 2 * u * k)).convert("RGBA")
    grad.putalpha(crown)
    L.alpha_composite(grad)
    edge = ImageChops.subtract(crown.filter(ImageFilter.MaxFilter(5)), crown)
    _put(L, edge, (120, 76, 14), alpha=0.85)

    band = _Mask(size)
    band.poly([(bx - 18 * u * k, by + 2 * u * k), (bx + 18 * u * k, by + 2 * u * k), (bx + 17 * u * k, by - 2 * u * k), (bx - 17 * u * k, by - 2 * u * k)])
    _put(L, band.get(), (190, 125, 30), alpha=0.9)
    shine = _Mask(size)
    shine.poly([(bx - 17 * u * k, by - 1 * u * k), (bx - 19 * u * k, by - 11 * u * k), (bx - 12 * u * k, by - 7 * u * k)])
    _put(L, shine.get(), (255, 255, 235), alpha=0.5)

    gems_w, gems_r = _Mask(size), _Mask(size)
    for gx, gy, gr in ((-20, -14, 2.0), (20, -14, 2.0)):
        gems_w.circle(bx + gx * u * k, by + gy * u * k, gr * u * 1.2)
    gems_r.circle(bx, by - 24 * u * k, 3.4 * u)
    _put(L, gems_w.get(), (255, 255, 255), blur=2.5 * u, strength=1.5)
    _put(L, gems_r.get(), (255, 70, 120), blur=3 * u, strength=1.5)

    fil = _Mask(size)                                     # filigree sparkles flanking the crown
    for ang in (-90 - 26, -90 + 26):
        x, y = _polar(mid, mid, ro + 6 * u, ang)
        fil.poly(_star_pts(x, y, 3.4 * u, 0.45))
    fil.poly(_star_pts(bx - 34 * u, by - 18 * u, 3.6 * u, 0.3))
    fil.poly(_star_pts(bx + 34 * u, by - 18 * u, 3.6 * u, 0.3))
    _put(L, fil.get(), (255, 240, 170), blur=2 * u, strength=1.4)


def _r_sakura(L, size, ri, th, u):
    """Soft pink gradient ring with cherry-blossom petals drifting around the border."""
    mid = size / 2
    ro = ri + th
    stops = [(255, 182, 213), (255, 214, 230), (255, 150, 196), (255, 196, 220), (255, 182, 213)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-30, bloom=6 * u, bloom_strength=0.8))
    hl = _Mask(size); hl.ring(ri + 1.2 * u, ri + 2.4 * u)
    _put(L, hl.get(), (255, 255, 255), alpha=0.4)

    rng = random.Random(5)
    shades = [(255, 196, 222), (255, 226, 238), (255, 168, 204)]
    petals = [_Mask(size) for _ in shades]
    inner = _Mask(size)
    for i in range(13):
        ang = i * 27.7 + rng.uniform(-8, 8)
        x, y = _polar(mid, mid, ro + rng.uniform(4, 17) * u, ang)
        length = (19 if i % 4 == 0 else rng.uniform(12, 17)) * u
        rot = rng.uniform(0, 360)
        bx, by = x - math.cos(math.radians(rot)) * length / 2, y - math.sin(math.radians(rot)) * length / 2
        petals[i % 3].poly(_petal_pts(bx, by, length, length * 0.42, rot))
        inner.poly(_petal_pts(bx + math.cos(math.radians(rot)) * length * 0.12,
                              by + math.sin(math.radians(rot)) * length * 0.12,
                              length * 0.62, length * 0.2, rot))
    glow_all = _Mask(size)
    for p in petals:
        glow_all.img = ImageChops.lighter(glow_all.img, p.img)
    L.alpha_composite(_glow(glow_all.get(), (255, 170, 210), 3 * u, 1.0))
    for p, color in zip(petals, shades):
        L.alpha_composite(_solid(p.get(), color, 0.94))
    _put(L, inner.get(), (255, 255, 255), alpha=0.5)
    dots = _Mask(size)
    for _ in range(7):
        x, y = _polar(mid, mid, ro + rng.uniform(6, 22) * u, rng.uniform(0, 360))
        dots.circle(x, y, 0.8 * u)
    _put(L, dots.get(), (255, 240, 205), blur=1.5 * u)


def _r_emerald(L, size, ri, th, u):
    """Deep-emerald-to-mint ring wrapped in a drifting green fog / aura with floating motes."""
    mid = size / 2
    ro = ri + th
    rng = random.Random(21)
    fog1, fog2 = _Mask(size), _Mask(size)
    for i in range(18):
        x, y = _polar(mid, mid, ro + rng.uniform(2, 9) * u, i * 20 + rng.uniform(-8, 8))
        fog1.circle(x, y, rng.uniform(11, 19) * u)
    for i in range(10):
        x, y = _polar(mid, mid, ro + rng.uniform(4, 13) * u, i * 36 + rng.uniform(-10, 10))
        fog2.circle(x, y, rng.uniform(6, 10) * u)
    L.alpha_composite(_solid(fog1.get().filter(ImageFilter.GaussianBlur(7 * u)), (40, 230, 150), 0.75))
    L.alpha_composite(_solid(fog2.get().filter(ImageFilter.GaussianBlur(4 * u)), (150, 255, 215), 0.55))

    stops = [(5, 90, 66), (30, 165, 116), (150, 255, 205), (30, 165, 116), (5, 90, 66)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-70, bloom=6 * u))
    hl = _Mask(size); hl.ring(ro - 2.2 * u, ro - 1 * u)
    _put(L, hl.get(), (200, 255, 230), alpha=0.5)
    motes = _Mask(size)
    for _ in range(11):
        x, y = _polar(mid, mid, ro + rng.uniform(10, 22) * u, rng.uniform(0, 360))
        motes.circle(x, y, rng.uniform(0.8, 1.5) * u)
    _put(L, motes.get(), (200, 255, 228), blur=2.2 * u, strength=1.6)


def _r_inferno(L, size, ri, th, u):
    """Orange-to-red ring with three nested layers of licking flame tongues and rising embers."""
    mid = size / 2
    t = th + 1 * u
    ro = ri + t
    rng = random.Random(9)
    tongues = []
    for i in range(22):
        length = rng.uniform(12, 20) * u * (1.15 if i % 3 == 0 else 1.0)
        tongues.append((i * 360 / 22 + rng.uniform(-3, 3), length, rng.choice([-1, 1]) * rng.uniform(3, 9)))
    layers = [((200, 24, 30), 1.0, 1.0), ((255, 104, 28), 0.74, 0.72), ((255, 206, 92), 0.46, 0.5)]
    for color, ls, ws in layers:
        mk = _Mask(size)
        for ang, length, curl in tongues:
            mk.poly(_flame_pts(mid, ro - 1.5 * u, ang, length * ls, 6.4 * ws, curl * ls))
        _put(L, mk.get(), color, blur=(4 * u if ls == 1.0 else 0), strength=1.2, alpha=0.96)

    stops = [(255, 190, 60), (255, 100, 30), (210, 30, 30), (255, 140, 40), (255, 190, 60)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-110, bloom=5 * u))
    hl = _Mask(size); hl.ring(ri + 1 * u, ri + 2.2 * u)
    _put(L, hl.get(), (255, 235, 160), alpha=0.5)
    embers = _Mask(size)
    for _ in range(9):
        x, y = _polar(mid, mid, ro + rng.uniform(17, 25) * u, rng.uniform(0, 360))
        embers.circle(x, y, rng.uniform(0.7, 1.4) * u)
    _put(L, embers.get(), (255, 196, 90), blur=2 * u, strength=1.6)


def _r_galaxy(L, size, ri, th, u):
    """Dark violet/indigo night-sky ring sprinkled with tiny glowing stars and twinkles."""
    mid = size / 2
    t = th + 1 * u
    ro = ri + t
    rng = random.Random(33)
    stops = [(30, 12, 80), (80, 60, 190), (150, 90, 230), (60, 40, 150), (30, 12, 80)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-25, bloom=7 * u, bloom_strength=1.1))
    for r0, r1 in ((ri, ri + 1 * u), (ro - 1 * u, ro)):   # light rims keep the dark ring readable
        e = _Mask(size); e.ring(r0, r1)
        _put(L, e.get(), (170, 150, 255), alpha=0.7)
    shimmer = _Mask(size); shimmer.ring(ro + 5 * u, ro + 6 * u)
    _put(L, shimmer.get(), (150, 130, 255), blur=2 * u, alpha=0.45)

    dots, twinkles = _Mask(size), _Mask(size)
    for _ in range(46):                                    # stars sitting on the ring
        x, y = _polar(mid, mid, rng.uniform(ri + 1 * u, ro - 1 * u), rng.uniform(0, 360))
        dots.circle(x, y, rng.uniform(0.6, 1.2) * u)
    for _ in range(16):                                    # distant stars outside
        x, y = _polar(mid, mid, ro + rng.uniform(3, 15) * u, rng.uniform(0, 360))
        dots.circle(x, y, rng.uniform(0.7, 1.5) * u)
    for ang in (-70, 20, 110, 200, 285):
        x, y = _polar(mid, mid, ro + rng.uniform(5, 14) * u, ang)
        twinkles.poly(_star_pts(x, y, rng.uniform(5, 7.5) * u, 0.22))
    _put(L, dots.get(), (255, 255, 255), blur=1.6 * u, strength=1.3)
    _put(L, twinkles.get(), (235, 225, 255), blur=2.6 * u, strength=1.6)


def _r_feather(L, size, ri, th, u):
    """Pearlescent white-silver ring with a glossy highlight and drifting feather wisps."""
    mid = size / 2
    t = th + 1 * u
    ro = ri + t
    stops = [(255, 255, 255), (214, 226, 248), (250, 226, 242), (222, 242, 250), (255, 255, 255)]
    m = _Mask(size); m.ring(ri, ro)
    L.alpha_composite(_conic_layer(m.get(), stops, rotate=-15, bloom=7 * u, bloom_strength=0.85))
    gloss = _Mask(size); gloss.arc(ri + 1 * u, ri + 3.6 * u, 200, 305)
    _put(L, gloss.get(), (255, 255, 255), alpha=0.8)

    rng = random.Random(14)
    soft, tinted, quills = _Mask(size), _Mask(size), _Mask(size)
    for i in range(14):
        ang = i * 360 / 14 + rng.uniform(-5, 5)
        length = (25 if i % 2 == 0 else 17) * u
        width = length * 0.2
        x, y = _polar(mid, mid, ro + 1 * u, ang)
        direction = ang + 90 - 24                          # sweep along the ring, leaning outward
        target = soft if i % 2 == 0 else tinted
        target.poly(_leaf_pts(x, y, length, width, direction, skew=0.25))
        dx, dy = math.cos(math.radians(direction)), math.sin(math.radians(direction))
        quills.line((x, y), (x + dx * length * 0.96, y + dy * length * 0.96), 0.55 * u)
        for f in (0.3, 0.5, 0.7):                          # barbs
            bx, by = x + dx * length * f, y + dy * length * f
            for side in (-1, 1):
                a = math.radians(direction + side * 52)
                quills.line((bx, by), (bx + math.cos(a) * width * 0.9, by + math.sin(a) * width * 0.9), 0.35 * u, 150)
    glow_src = _Mask(size)
    glow_src.img = ImageChops.lighter(soft.img, tinted.img)
    L.alpha_composite(_glow(glow_src.get(), (225, 232, 255), 3.4 * u, 1.1))
    L.alpha_composite(_solid(soft.get(), (255, 255, 255), 0.68))
    L.alpha_composite(_solid(tinted.get(), (243, 226, 255), 0.62))
    _put(L, quills.get(), (190, 202, 232), alpha=0.9)


def _r_vaporwave(L, size, ri, th, u):
    """Synthwave ring: cyan > purple > hot-pink, retro sunset slits, dual-tone edge lighting."""
    mid = size / 2
    t = th + 2 * u
    ro = ri + t
    m = _Mask(size); m.ring(ri, ro)
    ring_mask = m.get()
    # retro-sun slits cut across the lower half of the ring, widening toward the bottom
    cuts = Image.new("L", (size, size), 255)
    cd = ImageDraw.Draw(cuts)
    for k in range(5):
        y = mid + ro * (0.52 + k * 0.105)
        cd.rectangle((0, y, size, y + (1.1 + 0.7 * k) * u), fill=0)
    ring_mask = ImageChops.multiply(ring_mask, cuts)

    grad = _vgrad(size, [(0, 225, 255), (160, 70, 255), (255, 60, 170)],
                  int(mid - ro), int(mid + ro)).convert("RGBA")
    bloom_a = ring_mask.filter(ImageFilter.GaussianBlur(6 * u)).point(lambda v: min(255, int(v * 1.3)))
    bloom = grad.copy(); bloom.putalpha(bloom_a)
    L.alpha_composite(bloom)
    grad.putalpha(ring_mask)
    L.alpha_composite(grad)
    core = _Mask(size); core.ring(ri + t * 0.4, ri + t * 0.6)
    _put(L, ImageChops.multiply(core.get(), cuts), (255, 255, 255), alpha=0.35)

    cy_arc, pk_arc = _Mask(size), _Mask(size)             # dual-tone rim lights
    cy_arc.arc(ro + 3 * u, ro + 5.2 * u, 195, 295)
    pk_arc.arc(ro + 3 * u, ro + 5.2 * u, 15, 115)
    _put(L, cy_arc.get(), (0, 235, 255), blur=3 * u, strength=1.5)
    _put(L, pk_arc.get(), (255, 70, 185), blur=3 * u, strength=1.5)
    plus_c, plus_p = _Mask(size), _Mask(size)
    for mk, ang in ((plus_c, 235), (plus_p, 55)):
        x, y = _polar(mid, mid, ro + 14 * u, ang)
        mk.line((x - 4 * u, y), (x + 4 * u, y), 0.9 * u)
        mk.line((x, y - 4 * u), (x, y + 4 * u), 0.9 * u)
    _put(L, plus_c.get(), (150, 250, 255), blur=2 * u, strength=1.5)
    _put(L, plus_p.get(), (255, 150, 220), blur=2 * u, strength=1.5)


def _r_rainbow(L, size, ri, th, u):
    """Seamless spectrum ring under a glossy glass overlay with specular highlights."""
    mid = size / 2
    t = th + 2 * u
    ro = ri + t
    stops = []
    for i in range(13):
        r, g, b = colorsys.hsv_to_rgb((i % 12) / 12.0, 0.72, 1.0)
        stops.append((int(r * 255), int(g * 255), int(b * 255)))
    m = _Mask(size); m.ring(ri, ro)
    ring_mask = m.get()
    L.alpha_composite(_conic_layer(ring_mask, stops, rotate=-90, bloom=6 * u, bloom_strength=0.9))

    fade = Image.linear_gradient("L").rotate(180).resize((size, int(mid)))   # bright at the top
    top = Image.new("L", (size, size), 0)
    top.paste(fade, (0, 0))
    gloss_a = ImageChops.multiply(ImageChops.multiply(ring_mask, top), Image.new("L", (size, size), 215))
    gloss = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    gloss.putalpha(gloss_a)
    L.alpha_composite(gloss)
    for r0, r1, a in ((ri, ri + 0.9 * u, 0.5), (ro - 0.9 * u, ro, 0.45)):
        e = _Mask(size); e.ring(r0, r1)
        _put(L, e.get(), (255, 255, 255), alpha=a)
    spec = _Mask(size)
    x, y = _polar(mid, mid, ri + t / 2, -125)
    spec.circle(x, y, 1.7 * u)
    x2, y2 = _polar(mid, mid, ro + 9 * u, -48)
    spec.poly(_star_pts(x2, y2, 4.6 * u, 0.25))
    _put(L, spec.get(), (255, 255, 255), blur=2.4 * u, strength=1.5)


_RENDERERS = {
    "cyberpunk": _r_cyberpunk, "stardust": _r_stardust, "gold": _r_gold, "sakura": _r_sakura,
    "emerald": _r_emerald, "inferno": _r_inferno, "galaxy": _r_galaxy, "feather": _r_feather,
    "vaporwave": _r_vaporwave, "rainbow": _r_rainbow,
}


def draw_premium_ring(card, cx, cy, inner_r, thickness, shape):
    """
    Composite a premium border onto `card` (RGBA, modified in place).
      cx, cy    : centre of the avatar in card pixels
      inner_r   : radius where the ring begins (avatar radius + gap)
      thickness : base ring thickness in pixels (the card uses 8 * SCALE)
      shape     : one of PREMIUM_SHAPES
    """
    u = thickness / 8.0
    size = int(math.ceil((inner_r + thickness + 42 * u) * 2))
    size += size % 2
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _RENDERERS[shape](canvas, size, inner_r, thickness, u)
    card.alpha_composite(canvas, (int(cx - size // 2), int(cy - size // 2)))


# ---------------------------------------------------------------------------
# Standalone preview:  python premium_borders.py
# ---------------------------------------------------------------------------
def _preview(path="premium_preview.png"):
    scale, cell = 2, 360
    cols = 5
    names = list(PREMIUM_BORDERS)
    sheet = Image.new("RGB", (cell * cols, cell * math.ceil(len(names) / cols)), (24, 14, 44))
    for idx, code in enumerate(names):
        info = PREMIUM_BORDERS[code]
        w = cell * scale
        tile = Image.new("RGBA", (w, w), (28, 16, 52, 255))
        cx = cy = w // 2
        avatar_r, gap, ring = 62 * scale, 3 * scale, 6 * scale
        outer = avatar_r + gap + ring
        for key in ("glow2", "glow"):
            if key in info:
                halo = Image.new("RGBA", (w, w), (0, 0, 0, 0))
                off = (10 * scale if key == "glow2" else -4 * scale)
                ImageDraw.Draw(halo).ellipse((cx - outer - 14 * scale + off, cy - outer - 14 * scale,
                                              cx + outer + 14 * scale + off, cy + outer + 14 * scale), fill=info[key])
                tile = Image.alpha_composite(tile, halo.filter(ImageFilter.GaussianBlur(info["glow_blur"] * scale * 0.8)))
        draw_premium_ring(tile, cx, cy, avatar_r + gap, ring, info["shape"])
        d = ImageDraw.Draw(tile)
        d.ellipse((cx - avatar_r - gap, cy - avatar_r - gap, cx + avatar_r + gap, cy + avatar_r + gap), fill=(30, 16, 54, 255))
        d.ellipse((cx - avatar_r, cy - avatar_r, cx + avatar_r, cy + avatar_r), fill=(120, 150, 215, 255))
        tile = tile.resize((cell, cell), Image.Resampling.LANCZOS).convert("RGB")
        sheet.paste(tile, ((idx % cols) * cell, (idx // cols) * cell))
    sheet.save(path)
    print(f"saved {path}")


if __name__ == "__main__":
    _preview()
