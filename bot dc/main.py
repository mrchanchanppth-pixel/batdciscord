import asyncio
import io
import os
import re
import sqlite3
import unicodedata

import discord
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageOps

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
profile_lock = asyncio.Lock()


def setup_database():
    with sqlite3.connect("database.db") as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 1000,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            )
        """)


def get_user_data(user_id):
    with sqlite3.connect("database.db") as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,),
        )
        cursor = connection.execute(
            "SELECT balance, xp, level FROM users WHERE user_id = ?",
            (user_id,),
        )
        return cursor.fetchone()


def font_supports_text(font, text):
    try:
        missing_glyph = bytes(font.getmask("\U0010ffff"))
        for character in set(text):
            if character.isspace():
                continue
            if bytes(font.getmask(character)) == missing_glyph:
                return False
        return True
    except (OSError, ValueError):
        return True


def load_font(text, size, bold=True):
    if bold:
        font_paths = (
            "arialbd.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/ARIALUNI.TTF",
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/seguisym.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Bold.otf",
            "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSansKhmer-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        )
    else:
        font_paths = (
            "arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/ARIALUNI.TTF",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/seguisym.ttf",
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
            "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans.ttf",
        )

    fallback_font = None

    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            if fallback_font is None:
                fallback_font = font
            if font_supports_text(font, text):
                return font
        except OSError:
            continue

    return fallback_font or ImageFont.load_default()


def fit_font(draw, text, maximum_width, starting_size):
    for size in range(starting_size, 19, -2):
        font = load_font(text, size, True)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= maximum_width:
            return font
    return load_font(text, 18, True)


def draw_sharp_text(draw, position, text, font, fill):
    draw.text(
        position,
        text,
        font=font,
        fill=fill,
        stroke_width=3,
        stroke_fill=(0, 0, 0, 255),
    )


def sanitize_username(username):
    normalized = unicodedata.normalize("NFKD", username)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9 _.-]", "", ascii_name)
    safe_name = " ".join(safe_name.split()).strip()
    return safe_name or "Player"


def generate_profile_card(avatar_bytes, username, balance, level, xp):
    card_size = (1200, 480)
    username = sanitize_username(username)
    background = Image.open("background/bdg1.png")
    background = ImageOps.exif_transpose(background).convert("RGBA")
    background = ImageOps.fit(
        background,
        card_size,
        method=Image.Resampling.LANCZOS,
    )
    draw = ImageDraw.Draw(background)

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = ImageOps.fit(
        avatar,
        (250, 250),
        method=Image.Resampling.LANCZOS,
    )
    avatar_mask = Image.new("L", (250, 250), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, 249, 249), fill=255)

    draw.ellipse(
        (54, 94, 336, 376),
        fill=(0, 0, 0, 255),
    )
    draw.ellipse(
        (60, 100, 330, 370),
        fill=(255, 255, 255, 255),
    )
    draw.ellipse(
        (66, 106, 324, 364),
        fill=(45, 225, 255, 255),
    )
    background.paste(avatar, (70, 110), avatar_mask)

    header_text = "PLAYER PROFILE"
    username_font = fit_font(draw, username, 750, 58)
    header_font = load_font(header_text, 23, True)
    label_font = load_font("BALANCE LEVEL XP", 22, True)
    balance_text = f"${balance:,}"
    level_text = str(level)
    xp_text = f"{xp:,}"
    balance_font = fit_font(draw, balance_text, 250, 42)
    level_font = fit_font(draw, level_text, 180, 42)
    xp_font = fit_font(draw, xp_text, 220, 42)

    draw_sharp_text(
        draw,
        (390, 72),
        header_text,
        header_font,
        (54, 232, 255, 255),
    )
    draw_sharp_text(
        draw,
        (390, 118),
        username,
        username_font,
        (255, 255, 255, 255),
    )
    draw.line(
        (390, 205, 1100, 205),
        fill=(54, 232, 255, 255),
        width=5,
    )

    stat_columns = (
        (390, "BALANCE", balance_text, balance_font),
        (685, "LEVEL", level_text, level_font),
        (900, "XP", xp_text, xp_font),
    )

    for x, label, value, value_font in stat_columns:
        draw_sharp_text(
            draw,
            (x, 245),
            label,
            label_font,
            (54, 232, 255, 255),
        )
        draw_sharp_text(
            draw,
            (x, 292),
            value,
            value_font,
            (255, 255, 255, 255),
        )

    background.convert("RGB").save(
        "profile_card.png",
        "PNG",
        optimize=True,
    )


@client.event
async def on_ready():
    setup_database()
    print(f"Bot {client.user.name} is online!")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    user_text = message.content.strip().lower()

    if user_text == "hi":
        await message.channel.send(f"Hello, {message.author.display_name}!")

    elif user_text == "bal":
        balance, xp, level = get_user_data(message.author.id)
        await message.channel.send(f"Your current balance is: ${balance}")

    elif user_text in {"aup", "ap"}:
        balance, xp, level = get_user_data(message.author.id)
        avatar_bytes = await message.author.display_avatar.with_size(512).read()

        async with profile_lock:
            try:
                await asyncio.to_thread(
                    generate_profile_card,
                    avatar_bytes,
                    message.author.display_name,
                    balance,
                    level,
                    xp,
                )
                await message.channel.send(file=discord.File("profile_card.png"))
            finally:
                if os.path.exists("profile_card.png"):
                    os.remove("profile_card.png")


client.run(TOKEN)
