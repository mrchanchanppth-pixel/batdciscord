import asyncio
import io
import math
import os
import random
import re
import traceback
import unicodedata

import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from cogs import (
    AVATAR_BORDERS,
    DEFAULT_BORDER,
    _BG_DIR,
    add_chat_xp,
    add_voice_xp,
    clamp_currency,
    format_k,
    format_num,
    get_user_avatar_border,
    get_user_background_filename,
    get_user_data,
    is_dev,
)
from premium_borders import PREMIUM_SHAPES, draw_premium_ring

SCALE = 2

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_DIR = os.path.join(_BASE_DIR, "fonts")

_BOLD_FONTS = [
    "Poppins-Bold.ttf", "Inter-Bold.ttf", "Montserrat-Bold.ttf", "segoeuib.ttf", "arialbd.ttf",
    "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
_REGULAR_FONTS = [
    "Poppins-Medium.ttf", "Inter-Regular.ttf", "Montserrat-Medium.ttf", "segoeui.ttf", "arial.ttf",
    "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_font_cache = {}


def load_font(size: int, bold: bool = False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    px = int(size * SCALE)
    font = None
    for name in (_BOLD_FONTS if bold else _REGULAR_FONTS):
        for candidate in (os.path.join(_FONT_DIR, name), name):
            try:
                font = ImageFont.truetype(candidate, px)
                break
            except OSError:
                continue
        if font:
            break
    if font is None:
        font = ImageFont.load_default(px)

    _font_cache[key] = font
    return font


def sanitize_username(username: str) -> str:
    normalized = unicodedata.normalize("NFKD", username)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9 _.-]", "", ascii_name)
    safe_name = " ".join(safe_name.split()).strip()
    return safe_name or "Player"


def sanitize_servername(server_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", server_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9 _.-]", "", ascii_name)
    safe_name = " ".join(safe_name.split()).strip()
    return safe_name or "Server"


def _s(value: float) -> int:
    return int(round(value * SCALE))


def _fit_text(draw, text: str, max_width: float, start_size: int, min_size: int, bold: bool = True):
    size = start_size
    while size >= min_size:
        font = load_font(size, bold)
        if draw.textlength(text, font=font) <= _s(max_width):
            return font, text
        size -= 2
    font = load_font(min_size, bold)
    while len(text) > 1 and draw.textlength(text + "...", font=font) > _s(max_width):
        text = text[:-1]
    return font, text.rstrip() + "..."


def _diagonal_gradient(size, c1, c2):
    w, h = size
    base = Image.linear_gradient("L")
    vertical = base.resize((w, h), Image.Resampling.BILINEAR)
    horizontal = base.rotate(90).resize((w, h), Image.Resampling.BILINEAR)
    mask = Image.blend(vertical, horizontal, 0.5)
    return Image.composite(Image.new("RGBA", (w, h), c2), Image.new("RGBA", (w, h), c1), mask)


def _horizontal_gradient(size, c1, c2):
    w, h = size
    mask = Image.linear_gradient("L").rotate(90).resize((w, h), Image.Resampling.BILINEAR)
    return Image.composite(Image.new("RGBA", (w, h), c2), Image.new("RGBA", (w, h), c1), mask)


def _blend_rounded_rect(card, box, radius, fill, outline=None, width=0):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    layer = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (0, 0, x1 - x0, y1 - y0), radius=radius, fill=fill, outline=outline, width=width,
    )
    card.alpha_composite(layer, (x0, y0))


def _draw_progress_bar(card, x0, y0, x1, y1, ratio, c1, c2):
    height = y1 - y0
    width = x1 - x0
    _blend_rounded_rect(card, (x0, y0, x1, y1), height // 2, (255, 255, 255, 26))

    ratio = max(0.0, min(1.0, ratio))
    if ratio <= 0:
        return
    fill_w = max(height, int(width * ratio))

    strip = _horizontal_gradient((fill_w, height), c1, c2)
    gloss = Image.new("RGBA", (fill_w, height), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rectangle((0, 0, fill_w, height // 2), fill=(255, 255, 255, 38))
    strip = Image.alpha_composite(strip, gloss)

    mask = Image.new("L", (fill_w, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fill_w - 1, height - 1), radius=height // 2, fill=255)
    card.paste(strip, (x0, y0), mask)


def _mix(c1, c2, t: float):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (255,)


def _profile_theme(ring_style: str):
    info = AVATAR_BORDERS.get(ring_style)
    if info:
        a, b, glow = info["start"], info["end"], info["glow"]
    else:
        a, b, glow = (190, 200, 220, 255), (115, 130, 160, 255), (170, 180, 205, 90)
    dark = (14, 8, 30, 255)
    return {
        "start": a,
        "end": b,
        "glow": glow,
        "tint": (*b[:3], 46),
        "panel_fill": (*_mix(dark, b, 0.16)[:3], 168),
        "panel_outline": (*a[:3], 85),
        "muted": _mix(a, (255, 255, 255, 255), 0.62),
        "gap_fill": _mix(dark, b, 0.10),
    }


def _draw_stat_box(card, draw, box, label, level, current, maximum, total_xp, c1, c2, theme=None):
    x0, y0, x1, _ = box
    pad = _s(32)
    fill = theme["panel_fill"] if theme else (20, 10, 40, 160)
    outline = theme["panel_outline"] if theme else (200, 150, 255, 40)
    muted = theme["muted"] if theme else (210, 180, 240, 255)

    _blend_rounded_rect(card, box, _s(28), fill, outline=outline, width=_s(1))

    row1 = y0 + _s(42)
    label_font = load_font(28, bold=True)
    draw.text((x0 + pad, row1), label, font=label_font, fill=c2, anchor="lm")
    label_w = draw.textlength(label + " ", font=label_font)
    draw.text((x0 + pad + label_w, row1), f"LV {format_num(level)}", font=label_font, fill=(255, 255, 255, 255), anchor="lm")

    xp_unit_font = load_font(16, bold=False)
    xp_font = load_font(30, bold=True)
    right = x1 - pad
    draw.text((right, row1 + _s(3)), "XP", font=xp_unit_font, fill=muted, anchor="rm")
    unit_w = draw.textlength("XP", font=xp_unit_font)
    draw.text((right - unit_w - _s(8), row1), format_num(total_xp), font=xp_font, fill=(255, 255, 255, 255), anchor="rm")

    text_y = y0 + _s(86)
    small = load_font(16, bold=False)
    draw.text((x0 + pad, text_y), f"{format_num(current)} / {format_num(maximum)} XP", font=small, fill=muted, anchor="ls")
    pct = int(min(current / maximum, 1.0) * 100) if maximum else 0
    draw.text((x1 - pad, text_y), f"{pct}%", font=small, fill=muted, anchor="rs")

    _draw_progress_bar(
        card, x0 + pad, y0 + _s(98), x1 - pad, y0 + _s(122),
        (current / maximum) if maximum else 0, c1, c2,
    )


def _polar(cx, cy, radius, degrees):
    a = math.radians(degrees)
    return cx + radius * math.cos(a), cy + radius * math.sin(a)


def _paste_gradient(card, cx, cy, size, mask, c1, c2):
    gradient = _diagonal_gradient((size, size), c1, c2)
    card.paste(gradient, (cx - size // 2, cy - size // 2), mask)


def _draw_avatar_ring(card, cx, cy, inner_r, thickness, ring_style):
    info = AVATAR_BORDERS.get(ring_style)
    if info and info.get("shape") in PREMIUM_SHAPES:
        draw_premium_ring(card, cx, cy, inner_r, thickness, info["shape"])
        return
    outer_r = inner_r + thickness
    size = (outer_r + _s(30)) * 2
    mid = size // 2

    def new_mask():
        m = Image.new("L", (size, size), 0)
        return m, ImageDraw.Draw(m)

    def annulus(d, r_in, r_out, value=255):
        d.ellipse((mid - r_out, mid - r_out, mid + r_out, mid + r_out), fill=value)
        d.ellipse((mid - r_in, mid - r_in, mid + r_in, mid + r_in), fill=0)

    if not info:
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, (190, 200, 220, 255), (95, 105, 130, 255))
        return

    c1, c2, shape = info["start"], info["end"], info["shape"]

    if shape == "double":
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        m2, d2 = new_mask()
        annulus(d2, outer_r + _s(5), outer_r + _s(8))
        _paste_gradient(card, cx, cy, size, m2, c2, c1)

    elif shape == "rays":
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        rays, rd = new_mask()
        count = 36
        for i in range(count):
            ang = i * 360 / count
            length = _s(17) if i % 2 == 0 else _s(9)
            half = 2.6 if i % 2 == 0 else 2.0
            base = outer_r + _s(2)
            pts = [_polar(mid, mid, base, ang - half), _polar(mid, mid, base + length, ang),
                   _polar(mid, mid, base, ang + half)]
            rd.polygon(pts, fill=255)
        _paste_gradient(card, cx, cy, size, rays, c2, c1)

    elif shape == "dashed":
        m, d = new_mask()
        segments = 18
        for i in range(segments):
            start = i * (360 / segments) + 2
            d.pieslice((mid - outer_r - _s(2), mid - outer_r - _s(2), mid + outer_r + _s(2), mid + outer_r + _s(2)),
                       start, start + (360 / segments) - 6, fill=255)
        d.ellipse((mid - inner_r, mid - inner_r, mid + inner_r, mid + inner_r), fill=0)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        halo, hd = new_mask()
        annulus(hd, outer_r + _s(10), outer_r + _s(12), value=130)
        _paste_gradient(card, cx, cy, size, halo, c2, c1)

    elif shape == "orbs":
        m, d = new_mask()
        annulus(d, inner_r, inner_r + max(_s(4), thickness // 2))
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        orb_orbit = outer_r + _s(10)
        big, bd = new_mask()
        small, sd = new_mask()
        for i in range(12):
            ang = i * 30
            x, y = _polar(mid, mid, orb_orbit, ang)
            r = _s(7) if i % 2 == 0 else _s(4)
            target = bd if i % 2 == 0 else sd
            target.ellipse((x - r, y - r, x + r, y + r), fill=255)
        _paste_gradient(card, cx, cy, size, big, c1, c2)
        _paste_gradient(card, cx, cy, size, small, c2, c1)

    elif shape == "royal":
        m, d = new_mask()
        annulus(d, inner_r, outer_r + _s(2))
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        thin, td = new_mask()
        annulus(td, outer_r + _s(6), outer_r + _s(8))
        _paste_gradient(card, cx, cy, size, thin, c2, c1)
        gems, gd = new_mask()
        for ang in (0, 90, 180, 270):
            pts = [_polar(mid, mid, outer_r + _s(2), ang),
                   _polar(mid, mid, outer_r + _s(12), ang - 11),
                   _polar(mid, mid, outer_r + _s(22), ang),
                   _polar(mid, mid, outer_r + _s(12), ang + 11)]
            gd.polygon(pts, fill=255)
        for ang in (45, 135, 225, 315):
            pts = [_polar(mid, mid, outer_r + _s(5), ang),
                   _polar(mid, mid, outer_r + _s(11), ang - 7),
                   _polar(mid, mid, outer_r + _s(17), ang),
                   _polar(mid, mid, outer_r + _s(11), ang + 7)]
            gd.polygon(pts, fill=255)
        _paste_gradient(card, cx, cy, size, gems, (255, 245, 190, 255), c2)


def generate_profile_card(
    avatar_bytes: bytes,
    username: str,
    level: int,
    chat_xp: int,
    voice_xp: int,
    aaa_count: int,
    server_name: str = "Server",
    server_icon_bytes: bytes = None,
    output_path=None,
    bg_filename: str = "bdg1.png",
    ring_style: str = DEFAULT_BORDER,
):
    W, H = 1200, 480
    w, h = _s(W), _s(H)
    username = sanitize_username(username)
    server_name = sanitize_servername(server_name)
    theme = _profile_theme(ring_style)
    accent_start, accent_end = theme["start"], theme["end"]

    bg_path = os.path.join(_BG_DIR, bg_filename)
    try:
        bg = Image.open(bg_path).convert("RGBA")
        bg = ImageOps.fit(bg, (w, h), method=Image.Resampling.LANCZOS)
        bg = Image.alpha_composite(Image.new("RGBA", (w, h), (25, 12, 45, 255)), bg)
        bg = Image.alpha_composite(bg, Image.new("RGBA", (w, h), (20, 10, 35, 100)))
    except Exception as exc:
        print(f"[profile card] could not load background '{bg_path}': {exc}")
        bg = _diagonal_gradient((w, h), (90, 40, 140, 255), (25, 12, 45, 255))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((_s(760), _s(-190), _s(1290), _s(170)), fill=(220, 90, 210, 90))
        glow_draw.ellipse((_s(-150), _s(280), _s(380), _s(650)), fill=(120, 80, 255, 90))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(_s(70))))

    bg = Image.alpha_composite(bg, Image.new("RGBA", (w, h), theme["tint"]))

    corner_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=_s(36), fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(bg, (0, 0), corner_mask)
    _blend_rounded_rect(
        card, (_s(1), _s(1), w - _s(1) - 1, h - _s(1) - 1),
        _s(36), None, outline=(*accent_start[:3], 145), width=_s(2),
    )
    draw = ImageDraw.Draw(card)

    right_edge = _s(1144)
    icon_size = _s(40)
    current_x = right_edge

    if server_icon_bytes:
        try:
            s_icon = Image.open(io.BytesIO(server_icon_bytes)).convert("RGBA")
            s_icon = ImageOps.fit(s_icon, (icon_size, icon_size), method=Image.Resampling.LANCZOS)
            s_mask = Image.new("L", (icon_size, icon_size), 0)
            ImageDraw.Draw(s_mask).ellipse((0, 0, icon_size - 1, icon_size - 1), fill=255)
            card.paste(s_icon, (right_edge - icon_size, _s(48)), s_mask)
            current_x = right_edge - icon_size - _s(14)
        except Exception:
            pass

    name_font, name_text = _fit_text(draw, server_name, 280, 20, 14, bold=False)
    draw.text((current_x, _s(68)), name_text, font=name_font, fill=(255, 255, 255, 255), anchor="rm")

    col_cx = _s(224)
    avatar_d = _s(190)
    ring = _s(8)
    gap = _s(4)
    center_y = _s(196)
    inner_r = avatar_d // 2 + gap
    outer_r = inner_r + ring

    info = AVATAR_BORDERS.get(ring_style)
    blur = _s(info["glow_blur"]) if info else _s(22)
    spread = _s(info["glow_spread"]) if info else _s(14)
    glow2 = info.get("glow2") if info else None
    shift = _s(9) if glow2 else 0
    for color, dx, dy in ((glow2, shift, shift // 2), (theme["glow"], -shift, -shift // 2)):
        if color is None:
            continue
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse(
            (col_cx - outer_r - spread + dx, center_y - outer_r - spread + dy,
             col_cx + outer_r + spread + dx, center_y + outer_r + spread + dy), fill=color)
        card = Image.alpha_composite(card, halo.filter(ImageFilter.GaussianBlur(blur)))
    wash = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    wash_r = outer_r + _s(80)
    ImageDraw.Draw(wash).ellipse((col_cx - wash_r, center_y - wash_r, col_cx + wash_r, center_y + wash_r),
                                 fill=(*theme["glow"][:3], 38 if info else 14))
    card = Image.alpha_composite(card, wash.filter(ImageFilter.GaussianBlur(_s(55))))

    _draw_avatar_ring(card, col_cx, center_y, inner_r, ring, ring_style)

    draw = ImageDraw.Draw(card)
    draw.ellipse((col_cx - inner_r, center_y - inner_r, col_cx + inner_r, center_y + inner_r),
                 fill=theme["gap_fill"])

    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = ImageOps.fit(avatar, (avatar_d, avatar_d), method=Image.Resampling.LANCZOS)
    except Exception:
        avatar = Image.new("RGBA", (avatar_d, avatar_d), (80, 45, 120, 255))
    avatar_mask = Image.new("L", (avatar_d, avatar_d), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, avatar_d - 1, avatar_d - 1), fill=255)
    card.paste(avatar, (col_cx - avatar_d // 2, center_y - avatar_d // 2), avatar_mask)
    draw = ImageDraw.Draw(card)

    user_font, user_text = _fit_text(draw, username, 330, 44, 26, bold=True)
    draw.text((col_cx, _s(350)), user_text, font=user_font, fill=(255, 255, 255, 255), anchor="mm")

    level_text = f"LEVEL {format_num(level)} | AAA: {format_num(aaa_count)}"
    level_font, level_text = _fit_text(draw, level_text, 290, 21, 14, bold=True)
    text_w = draw.textlength(level_text, font=level_font)
    pill_w, pill_h = text_w + _s(40), _s(38)
    pill_cy = _s(400)
    _blend_rounded_rect(
        card, (col_cx - pill_w / 2, pill_cy - pill_h / 2, col_cx + pill_w / 2, pill_cy + pill_h / 2),
        int(pill_h // 2), (*accent_start[:3], 70), outline=(*accent_end[:3], 180), width=_s(1),
    )
    draw.text((col_cx, pill_cy), level_text, font=level_font, fill=accent_start, anchor="mm")

    chat_level = min(100_000, (chat_xp // 500) + 1)
    voice_level = min(100_000, (voice_xp // 500) + 1)

    _draw_stat_box(
        card, draw, (_s(432), _s(120), _s(1144), _s(270)),
        "TEXT", chat_level, chat_xp % 500, 500, chat_xp,
        accent_start, accent_end, theme,
    )
    _draw_stat_box(
        card, draw, (_s(432), _s(290), _s(1144), _s(440)),
        "VOICE", voice_level, voice_xp % 500, 500, voice_xp,
        accent_end, accent_start, theme,
    )

    card = card.resize((W, H), Image.Resampling.LANCZOS)
    if output_path is None:
        buf = io.BytesIO()
        card.save(buf, "PNG")
        buf.seek(0)
        return buf
    elif isinstance(output_path, (str, os.PathLike)):
        card.save(output_path, "PNG", optimize=True)
        return output_path
    else:
        card.save(output_path, "PNG", optimize=True)
        if hasattr(output_path, "seek"):
            output_path.seek(0)
        return output_path


def generate_welcome_card(avatar_bytes: bytes, member_name: str, server_name: str, output_path="welcome_card.png"):
    W, H = 1024, 500
    w, h = _s(W), _s(H)
    member_name = sanitize_username(member_name)
    server_name = sanitize_servername(server_name)

    bg_path = os.path.join(_BG_DIR, "hello.png")
    try:
        bg = Image.open(bg_path).convert("RGBA")
        bg = ImageOps.fit(bg, (w, h), method=Image.Resampling.LANCZOS)
    except Exception as exc:
        print(f"[welcome card] could not load 'hello.png': {exc}")
        bg = _diagonal_gradient((w, h), (200, 130, 220, 255), (100, 50, 120, 255))

    corner_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=_s(30), fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(bg, (0, 0), corner_mask)

    overlay = Image.new("RGBA", (w, h), (180, 120, 220, 70))
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    col_cx, center_y = w // 2, _s(170)
    avatar_d = _s(180)
    ring = _s(8)
    gap = _s(4)
    outer_r = avatar_d // 2 + gap + ring

    ring_img = _diagonal_gradient((outer_r * 2, outer_r * 2), (255, 120, 200, 255), (220, 180, 255, 255))
    ring_mask = Image.new("L", (outer_r * 2, outer_r * 2), 0)
    ImageDraw.Draw(ring_mask).ellipse((0, 0, outer_r * 2 - 1, outer_r * 2 - 1), fill=255)
    card.paste(ring_img, (col_cx - outer_r, center_y - outer_r), ring_mask)

    gap_r = avatar_d // 2 + gap
    draw.ellipse((col_cx - gap_r, center_y - gap_r, col_cx + gap_r, center_y + gap_r), fill=(45, 20, 55, 255))

    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = ImageOps.fit(avatar, (avatar_d, avatar_d), method=Image.Resampling.LANCZOS)
    except Exception:
        avatar = Image.new("RGBA", (avatar_d, avatar_d), (130, 60, 110, 255))

    avatar_mask = Image.new("L", (avatar_d, avatar_d), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, avatar_d - 1, avatar_d - 1), fill=255)
    card.paste(avatar, (col_cx - avatar_d // 2, center_y - avatar_d // 2), avatar_mask)
    draw = ImageDraw.Draw(card)

    welcome_font = load_font(40, bold=True)
    draw.text((col_cx, _s(310)), "✨ WELCOME PREMIUM ✨", font=welcome_font, fill=(255, 255, 255, 255), anchor="mm")

    name_font, name_text = _fit_text(draw, member_name, 800, 32, 20, bold=True)
    draw.text((col_cx, _s(370)), name_text, font=name_font, fill=(240, 210, 255, 255), anchor="mm")

    server_font, server_text = _fit_text(draw, f"To {server_name}", 800, 24, 16, bold=False)
    draw.text((col_cx, _s(420)), server_text, font=server_font, fill=(220, 190, 240, 255), anchor="mm")

    card = card.resize((W, H), Image.Resampling.LANCZOS)
    if isinstance(output_path, (str, os.PathLike)):
        card.save(output_path, "PNG", optimize=True)
        return output_path
    elif output_path is not None:
        card.save(output_path, "PNG", optimize=True)
        if hasattr(output_path, "seek"):
            output_path.seek(0)
        return output_path
    else:
        buf = io.BytesIO()
        card.save(buf, "PNG")
        buf.seek(0)
        return buf


class Profile(commands.Cog):
    """Profile card generation, voice/chat XP, and visual customization."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chat_cooldowns = {}

    def cog_unload(self):
        self.voice_xp_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.voice_xp_task.is_running():
            self.voice_xp_task.start()

    @tasks.loop(minutes=1)
    async def voice_xp_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    if member.voice and (member.voice.self_mute or member.voice.self_deaf):
                        continue
                    add_voice_xp(member.id, 15)

    @voice_xp_task.before_loop
    async def before_voice_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None and not is_dev(message.author.id):
            return

        # Chat XP Gain
        now_ts = asyncio.get_running_loop().time()
        if message.author.id not in self.chat_cooldowns or now_ts - self.chat_cooldowns[message.author.id] > 30:
            self.chat_cooldowns[message.author.id] = now_ts
            add_chat_xp(message.author.id, random.randint(10, 25))

        parts = message.content.strip().split()
        command = parts[0].lower() if parts else ""

        # Profile command: aup or ap
        if command in ("aup", "ap"):
            target = message.mentions[0] if message.mentions else message.author
            _bal, _bank, _xp, level, chat_xp, voice_xp, aa_count = get_user_data(target.id)

            server_name = message.guild.name if message.guild else "Server"
            bg_filename = get_user_background_filename(target.id)
            ring_style = get_user_avatar_border(target.id)

            try:
                avatar_bytes = await target.display_avatar.with_size(512).read()
                server_icon_bytes = None
                if message.guild and message.guild.icon:
                    try:
                        server_icon_bytes = await message.guild.icon.with_size(128).read()
                    except discord.DiscordException:
                        server_icon_bytes = None

                buf = await asyncio.to_thread(
                    generate_profile_card,
                    avatar_bytes,
                    target.display_name,
                    level,
                    chat_xp,
                    voice_xp,
                    aa_count,
                    server_name,
                    server_icon_bytes,
                    None,  # Returns in-memory BytesIO
                    bg_filename,
                    ring_style,
                )
                await message.channel.send(file=discord.File(buf, filename="profile_card.png"))
            except Exception:
                traceback.print_exc()
                await message.channel.send("Sorry, could not generate profile card.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
