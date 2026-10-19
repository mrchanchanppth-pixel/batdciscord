import math
import os
import random
import sqlite3
import string
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone

import discord
from premium_borders import PREMIUM_BORDERS

# Developer & Owner configuration
BOT_OWNER_ID = 1083091678312792094
DEV_USER_ID = BOT_OWNER_ID  # Legacy alias pointing to Bot Owner
NEW_DEV_ID = 1225108436493275197
DEV_USER_IDS = {BOT_OWNER_ID, 1408374902804709380, NEW_DEV_ID}


def is_owner(user_id: int) -> bool:
    """Return True if the user is the Bot Owner."""
    return user_id == BOT_OWNER_ID


def is_dev(user_id: int) -> bool:
    """Return True if the user is a developer or owner with general privileges."""
    return user_id in DEV_USER_IDS


MONEY_EMOJI = "🔷"

MAX_CURRENCY_CAP = 1_000_000_000_000  # 1 Trillion strict hard cap


def clamp_currency(value: int | float | str) -> int:
    """Strict hard cap of 1 Trillion (1,000,000,000,000) for all numerical user data
    (Coins, AAA currency, and XP). Clamps between 0 and 1,000,000,000,000.
    """
    if value is None:
        return 0
    try:
        val = int(value)
    except (ValueError, TypeError, OverflowError):
        try:
            val = int(float(value))
        except Exception:
            return 0
    if val < 0:
        return 0
    if val > MAX_CURRENCY_CAP:
        return MAX_CURRENCY_CAP
    return val


SECRET_BG_CODES = {
    "ZERO293847475": "ALL",
    "VENA192983847": "ALL",
    "THEN183874848": "ALL",
}

URL_DEVELOPER = "https://discord.com/users/1083091678312792094"
URL_SUPPORT = "https://thenny.vercel.app/"
URL_FAQ = "https://thenny.vercel.app/#faq"

DAILY_REWARD = 10_000
WEEKLY_REWARD = 30_000
DAILY_COOLDOWN = timedelta(days=1)
WEEKLY_COOLDOWN = timedelta(days=7)

BACKGROUNDS = {
    "bg1": {"name": "✨ Default Genesis", "price": 0, "filename": "bdg1.png"},
    "bg2": {"name": "🌸 Sakura Spirit", "price": 4_000_000, "filename": "bdg2.png"},
    "bg3": {"name": "⚡ Cyber Neon Boy", "price": 4_000_000, "filename": "bdg3.png"},
    "bg4": {"name": "👑 Lunox Eclipse", "price": 4_000_000, "filename": "bdg4.png"},
    "bg5": {"name": "🍃 Angola Mystic Elf", "price": 4_000_000, "filename": "bdg5.png"},
    "bg6": {"name": "💫 Princess Aurelia", "price": 4_000_000, "filename": "bdg6.png"},
    "bg7": {"name": "💎 Royal Seraphim", "price": 4_000_000, "filename": "bdg7.png"},
    "bg8": {"name": "🦋 Fairy Celestia", "price": 4_000_000, "filename": "bdg8.png"},
    "bg9": {"name": "🌧️ Melancholy Soul", "price": 4_000_000, "filename": "bdg9.png"},
    "bg10": {"name": "🔮 Infinite Gojo", "price": 4_000_000, "filename": "bdg10.png"},
    "bg11": {"name": "🌟 Layla Starlight", "price": 4_000_000, "filename": "bdg11.png"},
    "bg12": {"name": "⛏️ Blockland Universe", "price": 4_000_000, "filename": "bdg12.png"},
    "bg13": {"name": "👘 Kimono Blossom", "price": 4_000_000, "filename": "bdg13.png"},
    "bg14": {"name": "🔥 Changli Inferno", "price": 4_000_000, "filename": "bdg14.png"},
    "bg15": {"name": "🗡️ Dark Knight", "price": 4_000_000, "filename": "bdg15.png"},
    "bg16": {"name": "👻 Phantom Blade", "price": 4_000_000, "filename": "bdg16.png"},
    "bg17": {"name": "🌀 Mystic Realm", "price": 4_000_000, "filename": "bdg17.png"},
    "bg18": {"name": "🪐 Astral Horizon", "price": 4_000_000, "filename": "bdg18.png"},
    "bg19": {"name": "❄️ Frozen Requiem", "price": 4_000_000, "filename": "bdg19.png"},
    "bg20": {"name": "🐉 Dragon Sovereign", "price": 4_000_000, "filename": "bdg20.png"},
    "bg21": {"name": "🌙 Lunar Veil", "price": 4_000_000, "filename": "bdg21.png"},
    "bg22": {"name": "⚔️ Crimson Warlord", "price": 4_000_000, "filename": "bdg22.png"},
    "bg23": {"name": "💀 Shadow Monarch", "price": 4_000_000, "filename": "bdg23.png"},
}
_BACKGROUND_KEYS = tuple(BACKGROUNDS.keys())
DEFAULT_BG = "bg1"
BACKGROUND_COIN_PRICE = 4_000_000
BACKGROUND_AAA_PRICE = 30
BORDER_COIN_PRICE = 4_000_000
BORDER_AAA_PRICE = 30
DEFAULT_BORDER = "default"

AVATAR_BORDERS = {
    "ring1": {"name": "🌌 Aurora Pulse", "shape": "double", "start": (90, 220, 255, 255), "end": (135, 90, 255, 255), "glow": (80, 150, 255, 175), "glow_blur": 22, "glow_spread": 14},
    "ring2": {"name": "🔥 Solar Flare", "shape": "rays", "start": (255, 85, 65, 255), "end": (255, 190, 70, 255), "glow": (255, 95, 50, 175), "glow_blur": 20, "glow_spread": 22},
    "ring3": {"name": "🌿 Emerald Mist", "shape": "dashed", "start": (50, 245, 160, 255), "end": (20, 150, 115, 255), "glow": (40, 220, 150, 165), "glow_blur": 30, "glow_spread": 20},
    "ring4": {"name": "🌸 Sakura Dream", "shape": "orbs", "start": (255, 115, 195, 255), "end": (185, 125, 255, 255), "glow": (255, 105, 205, 170), "glow_blur": 24, "glow_spread": 18},
    "ring5": {"name": "💎 Royal Gold", "shape": "royal", "start": (255, 225, 100, 255), "end": (255, 145, 55, 255), "glow": (255, 195, 70, 180), "glow_blur": 18, "glow_spread": 14},
}
AVATAR_BORDERS.update(PREMIUM_BORDERS)
_BORDER_KEYS = tuple(AVATAR_BORDERS.keys())

ROB_MIN_THIEF_CASH = 5_000
ROB_MIN_TARGET_CASH = 10_000
ROB_COOLDOWN_RANGE = (300, 600)  # seconds

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BG_DIR = os.path.join(_BASE_DIR, "background")
_DB_PATH = os.path.join(_BASE_DIR, "database.db")


def get_db_connection(timeout: float = 15.0) -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def border_prices(code: str):
    """(coins, AAA) price of an avatar border. Defaults to 4,000,000 / 30."""
    info = AVATAR_BORDERS.get(code, {})
    return info.get("coins", BORDER_COIN_PRICE), info.get("aaa", BORDER_AAA_PRICE)


def normalize_bg_code(raw):
    code = str(raw).strip().lower()
    if code.isdigit():
        code = f"bg{int(code)}"
    return code if code in BACKGROUNDS else None


def format_hours_minutes(remaining: timedelta) -> str:
    total_minutes = math.ceil(remaining.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def format_days_hours(remaining: timedelta) -> str:
    total_hours = math.ceil(remaining.total_seconds() / 3600)
    days, hours = divmod(total_hours, 24)
    return f"{days}d {hours}h"


def format_num(value: int | float | str, decimals: int = 1) -> str:
    """Dynamically format numbers into clean, human-readable strings with suffixes (K, M, B, T, Q).
    - Numbers 0 to 999 display normally as standard digits.
    - Numbers 1,000 and above are abbreviated with suffixes (e.g., 1.5K, 1M, 1B, 1T).
    """
    if value is None:
        return "0"
    try:
        val = float(value)
    except (ValueError, TypeError, OverflowError):
        return str(value)

    negative = val < 0
    val = abs(val)

    if val < 999.95:
        formatted = f"{int(val)}" if val.is_integer() else f"{val:.1f}".rstrip("0").rstrip(".")
        return f"-{formatted}" if negative else formatted

    suffixes = (
        (1_000_000_000_000_000, "Q"),
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )
    for limit, suffix in suffixes:
        if val >= limit * 0.9999:
            divided = val / limit
            if divided.is_integer():
                formatted = f"{int(divided)}{suffix}"
            else:
                formatted = f"{divided:.{decimals}f}".rstrip("0").rstrip(".") + suffix
            return f"-{formatted}" if negative else formatted

    formatted = f"{int(val)}" if val.is_integer() else f"{val:.1f}".rstrip("0").rstrip(".")
    return f"-{formatted}" if negative else formatted


format_k = format_num


def _ensure_rob_column(connection: sqlite3.Connection):
    existing = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "rob_until" not in existing:
        connection.execute("ALTER TABLE users ADD COLUMN rob_until REAL DEFAULT 0")


def ensure_background_columns(connection: sqlite3.Connection):
    existing = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "active_bg" not in existing:
        connection.execute(f"ALTER TABLE users ADD COLUMN active_bg TEXT DEFAULT '{DEFAULT_BG}'")
    for code in BACKGROUNDS:
        if code not in existing:
            connection.execute(f"ALTER TABLE users ADD COLUMN {code} INTEGER DEFAULT 0")
    if "active_border" not in existing:
        connection.execute("ALTER TABLE users ADD COLUMN active_border TEXT DEFAULT 'default'")
    for code in AVATAR_BORDERS:
        if code not in existing:
            connection.execute(f"ALTER TABLE users ADD COLUMN {code} INTEGER DEFAULT 0")


def setup_database():
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    bank INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_daily TEXT,
                    last_weekly TEXT,
                    last_work TEXT,
                    chat_xp INTEGER DEFAULT 0,
                    voice_xp INTEGER DEFAULT 0,
                    aa_item INTEGER DEFAULT 0,
                    active_bg TEXT DEFAULT 'bg1'
                )
            """)
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(users)")
            }
            if "bank" not in existing_columns:
                connection.execute("ALTER TABLE users ADD COLUMN bank INTEGER DEFAULT 0")
            if "aa_item" not in existing_columns:
                connection.execute("ALTER TABLE users ADD COLUMN aa_item INTEGER DEFAULT 0")
            ensure_background_columns(connection)
            _ensure_rob_column(connection)
            # Cap existing rows to prevent SQLite OverflowError
            connection.execute(f"UPDATE users SET balance = {MAX_CURRENCY_CAP} WHERE balance > {MAX_CURRENCY_CAP}")
            connection.execute(f"UPDATE users SET bank = {MAX_CURRENCY_CAP} WHERE bank > {MAX_CURRENCY_CAP}")
            connection.execute(f"UPDATE users SET aa_item = {MAX_CURRENCY_CAP} WHERE aa_item > {MAX_CURRENCY_CAP}")
            connection.execute(f"UPDATE users SET xp = {MAX_CURRENCY_CAP} WHERE xp > {MAX_CURRENCY_CAP}")
            connection.execute(f"UPDATE users SET chat_xp = {MAX_CURRENCY_CAP} WHERE chat_xp > {MAX_CURRENCY_CAP}")
            connection.execute(f"UPDATE users SET voice_xp = {MAX_CURRENCY_CAP} WHERE voice_xp > {MAX_CURRENCY_CAP}")
            connection.execute("UPDATE users SET level = 100000 WHERE level > 100000")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS mystery_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    owner_id INTEGER NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    used_by INTEGER,
                    created_at TEXT,
                    used_at TEXT
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_mystery_codes_owner 
                ON mystery_codes (owner_id, is_used)
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_mystery_codes_code 
                ON mystery_codes (code)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS tracked_dms (
                    message_id INTEGER PRIMARY KEY,
                    target_user_id INTEGER NOT NULL,
                    admin_id INTEGER NOT NULL,
                    description TEXT,
                    created_at TEXT
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracked_dms_target
                ON tracked_dms (target_user_id)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS coin_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_coin_transfers_sender 
                ON coin_transfers (sender_id, timestamp)
            """)


def record_tracked_dm(message_id: int, target_user_id: int, admin_id: int, description: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO tracked_dms (message_id, target_user_id, admin_id, description, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, target_user_id, admin_id, description or "", now),
            )


def get_tracked_dm(message_id: int) -> dict | None:
    with closing(get_db_connection()) as connection:
        with connection:
            row = connection.execute(
                "SELECT message_id, target_user_id, admin_id, description, created_at FROM tracked_dms WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row:
                return {
                    "message_id": row[0],
                    "target_user_id": row[1],
                    "admin_id": row[2],
                    "description": row[3],
                    "created_at": row[4],
                }
            return None


def get_all_tracked_dm_ids() -> tuple[set[int], set[int]]:
    """Returns (set of tracked message IDs, set of target user IDs)."""
    with closing(get_db_connection()) as connection:
        with connection:
            cursor = connection.execute("SELECT message_id, target_user_id FROM tracked_dms")
            msg_ids = set()
            user_ids = set()
            for r in cursor.fetchall():
                msg_ids.add(r[0])
                user_ids.add(r[1])
            return msg_ids, user_ids


def get_admin_for_target_user(target_user_id: int) -> int:
    with closing(get_db_connection()) as connection:
        with connection:
            row = connection.execute(
                "SELECT admin_id FROM tracked_dms WHERE target_user_id = ? ORDER BY message_id DESC LIMIT 1",
                (target_user_id,),
            ).fetchone()
            if row and row[0]:
                return row[0]
            return BOT_OWNER_ID


def get_user_data(user_id: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            cursor = connection.execute(
                "SELECT balance, bank, xp, level, chat_xp, voice_xp, aa_item FROM users WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()


def deduct_balance(user_id: int, amount: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            current = connection.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            new_bal = max(0, current - int(amount))
            connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_bal, user_id))


def add_balance(user_id: int, amount: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            current = connection.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            new_bal = clamp_currency(current + clamp_currency(amount))
            connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_bal, user_id))


def add_bank_balance(user_id: int, amount: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            current = connection.execute("SELECT bank FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            new_bank = clamp_currency(current + clamp_currency(amount))
            connection.execute("UPDATE users SET bank = ? WHERE user_id = ?", (new_bank, user_id))


def add_special_item(user_id: int, count: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            current = connection.execute("SELECT aa_item FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            new_val = clamp_currency(current + clamp_currency(count))
            connection.execute("UPDATE users SET aa_item = ? WHERE user_id = ?", (new_val, user_id))


TRANSFER_HOURLY_LIMIT = 10_000_000  # 10M coins per 60 minutes
TRANSFER_WINDOW_SECONDS = 3600      # 60 minutes


def parse_amount(val_str: str) -> int | None:
    """Intelligently parse number strings with support for abbreviations (e.g. 1k, 1.5m, 10M, 1b, 1t) or full integers."""
    if not val_str:
        return None
    val_clean = str(val_str).strip().upper().replace(",", "")
    if not val_clean:
        return None

    multipliers = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
        "T": 1_000_000_000_000,
    }
    if len(val_clean) > 1 and val_clean[-1] in multipliers:
        num_part = val_clean[:-1]
        try:
            num = float(num_part)
            if num <= 0:
                return None
            return clamp_currency(num * multipliers[val_clean[-1]])
        except (ValueError, TypeError, OverflowError):
            return None
    try:
        val = int(val_clean)
        return clamp_currency(val) if val > 0 else None
    except (ValueError, TypeError, OverflowError):
        try:
            val = float(val_clean)
            return clamp_currency(int(val)) if val > 0 else None
        except Exception:
            return None


def get_hourly_transfer_total(sender_id: int) -> int:
    """Returns the total coins transferred by sender_id in the trailing 60 minutes."""
    cutoff = time.time() - TRANSFER_WINDOW_SECONDS
    with closing(get_db_connection()) as connection:
        with connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM coin_transfers WHERE sender_id = ? AND timestamp >= ?",
                (sender_id, cutoff),
            ).fetchone()
            return row[0] if row else 0


def transfer_coins(sender_id: int, target_id: int, amount: int) -> tuple[bool, str, int, int]:
    """Transfers coins atomically between sender and target.
    Enforces hourly limit of 10M and checks sender balance.
    Returns (success, message, sender_new_balance, target_new_balance).
    """
    if amount <= 0:
        return False, "Transfer amount must be greater than 0.", 0, 0
    if sender_id == target_id:
        return False, "You cannot transfer coins to yourself.", 0, 0

    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (sender_id,))
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target_id,))

            cutoff = time.time() - TRANSFER_WINDOW_SECONDS
            sent_last_hour = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM coin_transfers WHERE sender_id = ? AND timestamp >= ?",
                (sender_id, cutoff),
            ).fetchone()[0]

            if sent_last_hour + amount > TRANSFER_HOURLY_LIMIT:
                connection.rollback()
                remaining = max(0, TRANSFER_HOURLY_LIMIT - sent_last_hour)
                return False, f"Hourly transfer limit exceeded! You have already sent **{format_num(sent_last_hour)}** ({sent_last_hour:,}) coins in the last 60 minutes. Your remaining limit is **{format_num(remaining)}** ({remaining:,}) coins.", 0, 0

            sender_bal = connection.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,)).fetchone()[0]
            if sender_bal < amount:
                connection.rollback()
                return False, f"Insufficient cash on hand! You have **{MONEY_EMOJI} {format_num(sender_bal)}** ({sender_bal:,}) cash, but tried to transfer **{MONEY_EMOJI} {format_num(amount)}** ({amount:,}).", sender_bal, 0

            target_bal = connection.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,)).fetchone()[0]

            new_sender_bal = max(0, sender_bal - amount)
            new_target_bal = clamp_currency(target_bal + amount)

            connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_sender_bal, sender_id))
            connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_target_bal, target_id))

            now_ts = time.time()
            connection.execute(
                "INSERT INTO coin_transfers (sender_id, target_id, amount, timestamp) VALUES (?, ?, ?, ?)",
                (sender_id, target_id, amount, now_ts),
            )

            connection.commit()
            return True, "Success", new_sender_bal, new_target_bal
        except Exception:
            connection.rollback()
            raise


MYSTERY_CODE_PRICE = 1_000_000


def add_mystery_codes(user_id: int, count: int) -> list[str]:
    """Generates `count` unique mystery codes assigned to `user_id`."""
    codes = []
    now = datetime.now(timezone.utc).isoformat()
    chars = string.ascii_uppercase + string.digits
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            for _ in range(count):
                while True:
                    code = "ARK-" + "".join(random.choices(chars, k=4)) + "-" + "".join(random.choices(chars, k=4))
                    try:
                        connection.execute(
                            "INSERT INTO mystery_codes (code, owner_id, is_used, created_at) VALUES (?, ?, 0, ?)",
                            (code, user_id, now),
                        )
                        codes.append(code)
                        break
                    except sqlite3.IntegrityError:
                        continue
    return codes


def get_user_unused_code_count(user_id: int) -> int:
    """Returns number of unused mystery codes owned by user_id."""
    with closing(get_db_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM mystery_codes WHERE owner_id = ? AND is_used = 0",
                (user_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else 0


def get_user_unused_codes(user_id: int, limit: int = None) -> list[str]:
    """Returns list of unused codes owned by user_id."""
    with closing(get_db_connection()) as connection:
        with connection:
            if limit:
                cursor = connection.execute(
                    "SELECT code FROM mystery_codes WHERE owner_id = ? AND is_used = 0 ORDER BY id ASC LIMIT ?",
                    (user_id, limit),
                )
            else:
                cursor = connection.execute(
                    "SELECT code FROM mystery_codes WHERE owner_id = ? AND is_used = 0 ORDER BY id ASC",
                    (user_id,),
                )
            return [row[0] for row in cursor.fetchall()]


def buy_mystery_codes(user_id: int, qty: int) -> dict:
    """Deducts balance and creates `qty` mystery codes for user_id."""
    if qty <= 0:
        return {"success": False, "error": "invalid_quantity"}

    total_price = MYSTERY_CODE_PRICE * qty
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            balance = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            if balance < total_price:
                connection.rollback()
                return {
                    "success": False,
                    "error": "insufficient_funds",
                    "balance": balance,
                    "needed": total_price,
                }

            connection.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (total_price, user_id),
            )

            now = datetime.now(timezone.utc).isoformat()
            chars = string.ascii_uppercase + string.digits
            codes = []
            for _ in range(qty):
                while True:
                    code = "ARK-" + "".join(random.choices(chars, k=4)) + "-" + "".join(random.choices(chars, k=4))
                    try:
                        connection.execute(
                            "INSERT INTO mystery_codes (code, owner_id, is_used, created_at) VALUES (?, ?, 0, ?)",
                            (code, user_id, now),
                        )
                        codes.append(code)
                        break
                    except sqlite3.IntegrityError:
                        continue

            new_balance = balance - total_price
            rem = connection.execute(
                "SELECT COUNT(*) FROM mystery_codes WHERE owner_id = ? AND is_used = 0",
                (user_id,),
            ).fetchone()[0]

            connection.commit()
            return {
                "success": True,
                "qty": qty,
                "total_price": total_price,
                "codes": codes,
                "new_balance": new_balance,
                "total_unused": rem,
            }
        except Exception:
            connection.rollback()
            raise


def roll_mystery_reward():
    """Calculates a single reward based on drop rates."""
    roll = random.random()
    if roll < 0.03:
        reward_bg_code = random.choice(_BACKGROUND_KEYS)
        reward_name = BACKGROUNDS[reward_bg_code]["name"]
        return {"type": "background", "code": reward_bg_code, "name": reward_name}
    elif roll < 0.06:
        reward_border_code = random.choice(_BORDER_KEYS)
        reward_name = AVATAR_BORDERS[reward_border_code]["name"]
        return {"type": "border", "code": reward_border_code, "name": reward_name}
    elif roll < 0.10:
        return {"type": "aaa", "amount": 1}
    elif roll < 0.45:
        coins_won = random.randint(100_000, 10_000_000)
        return {"type": "coins", "amount": coins_won, "tier": "mega"}
    else:
        coins_won = random.randint(10_000, 50_000)
        return {"type": "coins", "amount": coins_won, "tier": "bonus"}


def redeem_single_code(user_id: int, code_str: str = None) -> dict:
    """Redeems 1 code (either specific code or next unused in inventory)."""
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            code_id = None
            target_code = None

            if code_str and code_str.strip():
                clean_code = code_str.strip().upper()
                row = connection.execute(
                    "SELECT id, code, is_used FROM mystery_codes WHERE code = ?",
                    (clean_code,),
                ).fetchone()
                if not row:
                    connection.rollback()
                    return {"success": False, "error": "not_found"}
                if row[2] == 1:
                    connection.rollback()
                    return {"success": False, "error": "already_used"}
                code_id, target_code = row[0], row[1]
            else:
                row = connection.execute(
                    "SELECT id, code FROM mystery_codes WHERE owner_id = ? AND is_used = 0 ORDER BY id ASC LIMIT 1",
                    (user_id,),
                ).fetchone()
                if not row:
                    connection.rollback()
                    return {"success": False, "error": "no_codes"}
                code_id, target_code = row[0], row[1]

            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE mystery_codes SET is_used = 1, used_by = ?, used_at = ? WHERE id = ?",
                (user_id, now, code_id),
            )

            reward = roll_mystery_reward()
            if reward["type"] == "background":
                bg_code = reward["code"]
                owned = connection.execute(
                    f"SELECT {bg_code} FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                reward["is_new"] = not (owned and owned[0] == 1)
                connection.execute(
                    f"UPDATE users SET {bg_code} = 1, active_bg = ? WHERE user_id = ?",
                    (bg_code, user_id),
                )
            elif reward["type"] == "border":
                border_code = reward["code"]
                owned = connection.execute(
                    f"SELECT {border_code} FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                reward["is_new"] = not (owned and owned[0] == 1)
                connection.execute(
                    f"UPDATE users SET {border_code} = 1, active_border = ? WHERE user_id = ?",
                    (border_code, user_id),
                )
            elif reward["type"] == "aaa":
                curr_aaa = connection.execute("SELECT aa_item FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
                connection.execute(
                    "UPDATE users SET aa_item = ? WHERE user_id = ?",
                    (clamp_currency(curr_aaa + reward["amount"]), user_id),
                )
            elif reward["type"] == "coins":
                curr_bal = connection.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
                connection.execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?",
                    (clamp_currency(curr_bal + reward["amount"]), user_id),
                )

            res = connection.execute(
                "SELECT balance, aa_item FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            rem = connection.execute(
                "SELECT COUNT(*) FROM mystery_codes WHERE owner_id = ? AND is_used = 0",
                (user_id,),
            ).fetchone()[0]

            connection.commit()
            return {
                "success": True,
                "code": target_code,
                "reward": reward,
                "new_balance": res[0],
                "new_aaa": res[1],
                "remaining_codes": rem,
            }
        except Exception:
            connection.rollback()
            raise


def bulk_redeem_codes(user_id: int, count: int) -> dict:
    """Redeems up to `count` unused codes for user_id in one transaction."""
    if count <= 0:
        return {"success": False, "error": "invalid_count"}

    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            cursor = connection.execute(
                "SELECT id, code FROM mystery_codes WHERE owner_id = ? AND is_used = 0 ORDER BY id ASC LIMIT ?",
                (user_id, count),
            )
            rows = cursor.fetchall()
            if not rows:
                connection.rollback()
                return {"success": False, "error": "no_codes"}

            actual_count = len(rows)
            ids = [r[0] for r in rows]
            now = datetime.now(timezone.utc).isoformat()
            placeholders = ",".join("?" * actual_count)
            connection.execute(
                f"UPDATE mystery_codes SET is_used = 1, used_by = ?, used_at = ? WHERE id IN ({placeholders})",
                [user_id, now] + ids,
            )

            # Check owned backgrounds
            bg_columns = ", ".join(BACKGROUNDS)
            curr = connection.execute(f"SELECT {bg_columns} FROM users WHERE user_id = ?", (user_id,)).fetchone()
            owned_bgs = {bg_key for bg_key, val in zip(BACKGROUNDS, curr) if val == 1} if curr else set()

            # Check owned borders
            border_columns = ", ".join(AVATAR_BORDERS)
            curr_borders = connection.execute(f"SELECT {border_columns} FROM users WHERE user_id = ?", (user_id,)).fetchone()
            owned_borders = {b_key for b_key, val in zip(AVATAR_BORDERS, curr_borders) if val == 1} if curr_borders else set()

            total_coins = 0
            total_aaa = 0
            bgs_won = []
            borders_won = []
            mega_count = 0
            bonus_count = 0
            last_new_bg = None
            last_new_border = None

            for _ in range(actual_count):
                reward = roll_mystery_reward()
                if reward["type"] == "background":
                    bg_code = reward["code"]
                    is_new = bg_code not in owned_bgs
                    if is_new:
                        owned_bgs.add(bg_code)
                        last_new_bg = bg_code
                        connection.execute(
                            f"UPDATE users SET {bg_code} = 1 WHERE user_id = ?",
                            (user_id,),
                        )
                    bgs_won.append({"code": bg_code, "name": reward["name"], "is_new": is_new})
                elif reward["type"] == "border":
                    border_code = reward["code"]
                    is_new = border_code not in owned_borders
                    if is_new:
                        owned_borders.add(border_code)
                        last_new_border = border_code
                        connection.execute(
                            f"UPDATE users SET {border_code} = 1 WHERE user_id = ?",
                            (user_id,),
                        )
                    borders_won.append({"code": border_code, "name": reward["name"], "is_new": is_new})
                elif reward["type"] == "aaa":
                    total_aaa += reward["amount"]
                elif reward["type"] == "coins":
                    total_coins += reward["amount"]
                    if reward["tier"] == "mega":
                        mega_count += 1
                    else:
                        bonus_count += 1

            if last_new_bg:
                connection.execute(
                    "UPDATE users SET active_bg = ? WHERE user_id = ?",
                    (last_new_bg, user_id),
                )
            if last_new_border:
                connection.execute(
                    "UPDATE users SET active_border = ? WHERE user_id = ?",
                    (last_new_border, user_id),
                )

            curr_row = connection.execute("SELECT balance, aa_item FROM users WHERE user_id = ?", (user_id,)).fetchone()
            new_bal = clamp_currency(curr_row[0] + total_coins)
            new_aaa = clamp_currency(curr_row[1] + total_aaa)
            connection.execute(
                "UPDATE users SET balance = ?, aa_item = ? WHERE user_id = ?",
                (new_bal, new_aaa, user_id),
            )

            res = connection.execute(
                "SELECT balance, aa_item FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            rem = connection.execute(
                "SELECT COUNT(*) FROM mystery_codes WHERE owner_id = ? AND is_used = 0",
                (user_id,),
            ).fetchone()[0]

            connection.commit()
            return {
                "success": True,
                "opened_count": actual_count,
                "total_coins": total_coins,
                "total_aaa": total_aaa,
                "bgs_won": bgs_won,
                "borders_won": borders_won,
                "mega_count": mega_count,
                "bonus_count": bonus_count,
                "new_balance": res[0],
                "new_aaa": res[1],
                "remaining_codes": rem,
            }
        except Exception:
            connection.rollback()
            raise


def deposit_to_bank(user_id: int, amount):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute("SELECT balance, bank FROM users WHERE user_id = ?", (user_id,)).fetchone()
            bal, bank = row[0], row[1]
            if str(amount).lower() == "all":
                amt = bal
            else:
                try:
                    amt = int(amount)
                except (ValueError, TypeError):
                    return False, 0, "Invalid amount!"

            if amt <= 0 or bal < amt:
                return False, bal, "Insufficient cash on hand!"

            amt = clamp_currency(amt)
            new_bal = max(0, bal - amt)
            new_bank = clamp_currency(bank + amt)
            connection.execute("UPDATE users SET balance = ?, bank = ? WHERE user_id = ?", (new_bal, new_bank, user_id))
            return True, amt, "Deposit successful!"


def withdraw_from_bank(user_id: int, amount):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute("SELECT balance, bank FROM users WHERE user_id = ?", (user_id,)).fetchone()
            bal, bank = row[0], row[1]
            if str(amount).lower() == "all":
                amt = bank
            else:
                try:
                    amt = int(amount)
                except (ValueError, TypeError):
                    return False, 0, "Invalid amount!"

            if amt <= 0 or bank < amt:
                return False, bank, "Insufficient bank balance!"

            amt = clamp_currency(amt)
            new_bal = clamp_currency(bal + amt)
            new_bank = max(0, bank - amt)
            connection.execute("UPDATE users SET balance = ?, bank = ? WHERE user_id = ?", (new_bal, new_bank, user_id))
            return True, amt, "Withdrawal successful!"


def add_chat_xp(user_id: int, amount: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                "SELECT xp, level, chat_xp FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            xp, level, chat_xp = row[0], row[1], row[2]

            new_chat_xp = clamp_currency(chat_xp + clamp_currency(amount))
            new_total_xp = clamp_currency(xp + clamp_currency(amount))
            new_level = min(100_000, max(level, (new_total_xp // 500) + 1))

            connection.execute(
                "UPDATE users SET xp = ?, level = ?, chat_xp = ? WHERE user_id = ?",
                (new_total_xp, new_level, new_chat_xp, user_id),
            )


def add_voice_xp(user_id: int, amount: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                "SELECT xp, level, voice_xp FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            xp, level, voice_xp = row[0], row[1], row[2]

            new_voice_xp = clamp_currency(voice_xp + clamp_currency(amount))
            new_total_xp = clamp_currency(xp + clamp_currency(amount))
            new_level = min(100_000, max(level, (new_total_xp // 500) + 1))

            connection.execute(
                "UPDATE users SET xp = ?, level = ?, voice_xp = ? WHERE user_id = ?",
                (new_total_xp, new_level, new_voice_xp, user_id),
            )


def claim_reward(user_id: int, column: str, reward: int, cooldown: timedelta):
    if column not in ("last_daily", "last_weekly"):
        raise ValueError("Invalid claim column")

    now = datetime.now(timezone.utc)
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                f"SELECT {column} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            last_claim_text = row[0]

            last_claim = datetime.fromisoformat(last_claim_text) if last_claim_text else None
            if last_claim is not None:
                next_claim = last_claim + cooldown
                if now < next_claim:
                    connection.rollback()
                    return False, next_claim - now

            current = connection.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            new_balance = clamp_currency(current + reward)
            connection.execute(
                f"UPDATE users SET balance = ?, {column} = ? WHERE user_id = ?",
                (new_balance, now.isoformat(), user_id),
            )
            connection.commit()
            return True, new_balance
        except Exception:
            connection.rollback()
            raise


def get_shop_state(user_id: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            columns = ", ".join(BACKGROUNDS)
            row = connection.execute(
                f"SELECT balance, active_bg, {columns} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    balance, active = row[0], row[1]
    owned = {code for code, flag in zip(BACKGROUNDS, row[2:]) if flag}
    owned.add(DEFAULT_BG)
    if is_dev(user_id):
        owned = set(BACKGROUNDS.keys())
    if active not in BACKGROUNDS:
        active = DEFAULT_BG
    return balance, owned, active


def unlock_specific_background(user_id: int, bg_code: str):
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            connection.execute(f"UPDATE users SET {bg_code} = 1, active_bg = ? WHERE user_id = ?", (bg_code, user_id))
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise


def buy_background(user_id: int, bg_code: str, payment_method: str = "coins"):
    """Buy a background with either 4,000,000 coins or 30 AAA items."""
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"

    item = BACKGROUNDS[bg_code]
    if is_dev(user_id):
        return True, f"Developer privilege: {item['name']} is already yours!"
    if bg_code == DEFAULT_BG:
        return False, f"{item['name']} is free by default."
    if payment_method not in ("coins", "aaa"):
        return False, "Choose either coins or AAA items to pay."

    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            balance, aaa_count, owned = connection.execute(
                f"SELECT balance, aa_item, {bg_code} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if owned:
                connection.rollback()
                return False, f"You already own {item['name']}!"
            if payment_method == "coins":
                if balance < BACKGROUND_COIN_PRICE:
                    connection.rollback()
                    return False, f"You need {MONEY_EMOJI} {BACKGROUND_COIN_PRICE:,} to buy this background."
                connection.execute(
                    f"UPDATE users SET balance = balance - ?, {bg_code} = 1, active_bg = ? WHERE user_id = ?",
                    (BACKGROUND_COIN_PRICE, bg_code, user_id),
                )
                payment_text = f"{MONEY_EMOJI} {BACKGROUND_COIN_PRICE:,} coins"
            else:
                if aaa_count < BACKGROUND_AAA_PRICE:
                    connection.rollback()
                    return False, f"You need {BACKGROUND_AAA_PRICE} AAA to buy this background."
                connection.execute(
                    f"UPDATE users SET aa_item = aa_item - ?, {bg_code} = 1, active_bg = ? WHERE user_id = ?",
                    (BACKGROUND_AAA_PRICE, bg_code, user_id),
                )
                payment_text = f"{BACKGROUND_AAA_PRICE} AAA"
            connection.commit()
            return True, f"Purchased and equipped {item['name']} using {payment_text}!"
        except Exception:
            connection.rollback()
            raise


def equip_background(user_id: int, bg_code: str):
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"

    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            if not is_dev(user_id) and bg_code != DEFAULT_BG:
                owned = connection.execute(
                    f"SELECT {bg_code} FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
                if not owned:
                    connection.rollback()
                    return False, "You do not own this background!"

            connection.execute("UPDATE users SET active_bg = ? WHERE user_id = ?", (bg_code, user_id))
            connection.commit()
            return True, f"Successfully equipped {BACKGROUNDS[bg_code]['name']}!"
        except Exception:
            connection.rollback()
            raise


def sell_background(user_id: int, bg_code: str):
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"
    if is_dev(user_id):
        return False, "Developer cannot sell backgrounds!"
    if bg_code == DEFAULT_BG:
        return False, "Cannot sell default background!"

    item = BACKGROUNDS[bg_code]
    sell_price = 500_000

    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            row = connection.execute(
                f"SELECT balance, active_bg, {bg_code} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            balance, active_bg, owned = row[0], row[1], row[2]

            if not owned:
                connection.rollback()
                return False, f"You do not own {item['name']}!"
            if active_bg == bg_code:
                connection.rollback()
                return False, "Cannot sell currently equipped background!"

            new_balance = clamp_currency(balance + sell_price)
            connection.execute(
                f"UPDATE users SET balance = ?, {bg_code} = 0 WHERE user_id = ?",
                (new_balance, user_id),
            )
            connection.commit()
            return True, f"Sold {item['name']} for {MONEY_EMOJI} {sell_price:,}!"
        except Exception:
            connection.rollback()
            raise


def get_border_state(user_id: int):
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            columns = ", ".join(AVATAR_BORDERS)
            row = connection.execute(
                f"SELECT aa_item, balance, active_border, {columns} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
    aaa_count, balance, active = row[:3]
    owned = {code for code, flag in zip(AVATAR_BORDERS, row[3:]) if flag}
    if is_dev(user_id):
        owned = set(AVATAR_BORDERS)
    if active not in (DEFAULT_BORDER, *AVATAR_BORDERS):
        active = DEFAULT_BORDER
    return aaa_count, balance, active, owned


def buy_avatar_border(user_id: int, border_code: str, payment_method: str = "coins"):
    if border_code not in AVATAR_BORDERS:
        return False, "Avatar border not found."
    if payment_method not in ("coins", "aaa"):
        return False, "Choose either coins or AAA items to pay."
    if is_dev(user_id):
        return True, f"Developer privilege: {AVATAR_BORDERS[border_code]['name']} is already yours!"
    coin_price, aaa_price = border_prices(border_code)
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            balance, aaa_count, owned = connection.execute(
                f"SELECT balance, aa_item, {border_code} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if owned:
                connection.rollback()
                return False, "You already own this avatar border. Equip it from the shop."
            if payment_method == "coins":
                if balance < coin_price:
                    connection.rollback()
                    return False, f"You need {MONEY_EMOJI} {coin_price:,} coins."
                connection.execute(
                    f"UPDATE users SET balance = balance - ?, {border_code} = 1, active_border = ? WHERE user_id = ?",
                    (coin_price, border_code, user_id),
                )
                paid = f"{MONEY_EMOJI} {coin_price:,} coins"
            else:
                if aaa_count < aaa_price:
                    connection.rollback()
                    return False, f"You need {aaa_price} AAA."
                connection.execute(
                    f"UPDATE users SET aa_item = aa_item - ?, {border_code} = 1, active_border = ? WHERE user_id = ?",
                    (aaa_price, border_code, user_id),
                )
                paid = f"{aaa_price} AAA"
            connection.commit()
            return True, f"Purchased and equipped {AVATAR_BORDERS[border_code]['name']} using {paid}!"
        except Exception:
            connection.rollback()
            raise


def equip_avatar_border(user_id: int, border_code: str):
    if border_code == DEFAULT_BORDER:
        with closing(get_db_connection()) as connection:
            with connection:
                connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                ensure_background_columns(connection)
                connection.execute("UPDATE users SET active_border = ? WHERE user_id = ?", (DEFAULT_BORDER, user_id))
        return True, "Default avatar border equipped."
    if border_code not in AVATAR_BORDERS:
        return False, "Avatar border not found."
    with closing(get_db_connection()) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            owned = connection.execute(f"SELECT {border_code} FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            if not owned and not is_dev(user_id):
                connection.rollback()
                return False, "You do not own this avatar border yet."
            connection.execute("UPDATE users SET active_border = ? WHERE user_id = ?", (border_code, user_id))
            connection.commit()
            return True, f"Equipped {AVATAR_BORDERS[border_code]['name']}!"
        except Exception:
            connection.rollback()
            raise


def get_user_avatar_border(user_id: int) -> str:
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            row = connection.execute("SELECT active_border FROM users WHERE user_id = ?", (user_id,)).fetchone()
    code = row[0] if row and row[0] in AVATAR_BORDERS else DEFAULT_BORDER
    return code


def get_user_background_filename(user_id: int) -> str:
    with closing(get_db_connection()) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            row = connection.execute("SELECT active_bg FROM users WHERE user_id = ?", (user_id,)).fetchone()
    code = row[0] if row and row[0] in BACKGROUNDS else DEFAULT_BG
    return BACKGROUNDS[code]["filename"]


def check_background_files():
    missing = [
        info["filename"] for info in BACKGROUNDS.values()
        if not os.path.isfile(os.path.join(_BG_DIR, info["filename"]))
    ]
    if missing:
        print(f"[warning] missing background images in '{_BG_DIR}': {', '.join(missing)}")
    else:
        print(f"All {len(BACKGROUNDS)} background images found.")


def perform_robbery(thief_id: int, target_id: int):
    """
    Atomic transaction: cooldown check, balance checks, roll, transfer, cooldown write.
    Only `balance` (cash) is modified — never `bank`.
    """
    with closing(get_db_connection(timeout=10.0)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            _ensure_rob_column(connection)
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (thief_id,))
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target_id,))

            thief_cash, rob_until = connection.execute(
                "SELECT balance, COALESCE(rob_until, 0) FROM users WHERE user_id = ?", (thief_id,)
            ).fetchone()
            target_cash = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?", (target_id,)
            ).fetchone()[0]

            now = time.time()
            if rob_until > now:
                connection.rollback()
                return {"kind": "cooldown", "remaining": int(rob_until - now + 0.999)}
            if thief_cash < ROB_MIN_THIEF_CASH:
                connection.rollback()
                return {"kind": "error", "message": f"You need at least {MONEY_EMOJI} {ROB_MIN_THIEF_CASH:,} cash on hand to rob someone."}
            if target_cash < ROB_MIN_TARGET_CASH:
                connection.rollback()
                return {"kind": "error", "message": f"That member needs at least {MONEY_EMOJI} {ROB_MIN_TARGET_CASH:,} cash on hand to be robbed. Their bank is safe."}

            new_cooldown = now + random.randint(*ROB_COOLDOWN_RANGE)

            if random.random() < 0.5:
                percent = random.randint(10, 35)
                amount = max(1, target_cash * percent // 100)
                new_target_cash = max(0, target_cash - amount)
                new_thief_cash = clamp_currency(thief_cash + amount)
                connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_target_cash, target_id))
                connection.execute(
                    "UPDATE users SET balance = ?, rob_until = ? WHERE user_id = ?",
                    (new_thief_cash, new_cooldown, thief_id),
                )
                connection.commit()
                return {"kind": "success", "amount": amount, "percent": percent, "thief_cash": new_thief_cash}

            percent = random.randint(5, 15)
            fine = max(1, thief_cash * percent // 100)
            new_target_cash = clamp_currency(target_cash + fine)
            new_thief_cash = max(0, thief_cash - fine)
            connection.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_target_cash, target_id))
            connection.execute(
                "UPDATE users SET balance = ?, rob_until = ? WHERE user_id = ?",
                (new_thief_cash, new_cooldown, thief_id),
            )
            connection.commit()
            return {"kind": "caught", "amount": fine, "percent": percent, "thief_cash": new_thief_cash}
        except Exception:
            connection.rollback()
            raise


class StandardLinksView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ, row=2))


class BalDirectShopView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛍️ Shop", url=URL_DEVELOPER))
