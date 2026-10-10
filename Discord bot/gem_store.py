import asyncio
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


STARTING_GEMS = 1_000
MAX_LEVEL = 100
XP_PER_LEVEL = 100
MAX_SQLITE_INTEGER = 9_223_372_036_854_775_807
DAILY_CLAIM_GEMS = 100
DAILY_CLAIM_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class GemAccount:
    user_id: int
    balance: int
    xp: int

    @property
    def level(self) -> int:
        return min(MAX_LEVEL, 1 + self.xp // XP_PER_LEVEL)

    @property
    def xp_into_level(self) -> int:
        if self.level == MAX_LEVEL:
            return 0
        return self.xp % XP_PER_LEVEL


class GemStore:
    def __init__(self, database_path: Optional[Path] = None) -> None:
        self.database_path = database_path or Path(__file__).with_name("gems.sqlite3")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _ensure_account(self, connection: sqlite3.Connection, user_id: int) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO gem_accounts (user_id, balance, xp) VALUES (?, ?, 0)",
            (user_id, STARTING_GEMS),
        )

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS gem_accounts (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_gem_claims (
                    user_id INTEGER PRIMARY KEY,
                    claimed_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS multiplayer_escrows (
                    match_id TEXT PRIMARY KEY,
                    player_one INTEGER NOT NULL,
                    player_two INTEGER NOT NULL,
                    stake INTEGER NOT NULL CHECK (stake > 0),
                    status TEXT NOT NULL CHECK (status IN ('pending', 'settled'))
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_game_escrows (
                    match_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    stake INTEGER NOT NULL CHECK (stake > 0),
                    status TEXT NOT NULL CHECK (status IN ('pending', 'settled'))
                )
                """
            )

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize)

    def _get_account(self, user_id: int) -> GemAccount:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            row = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return GemAccount(user_id, int(row[0]), int(row[1]))

    async def get_account(self, user_id: int) -> GemAccount:
        return await asyncio.to_thread(self._get_account, user_id)

    def _transfer(self, sender_id: int, recipient_id: int, amount: int) -> Tuple[bool, int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, sender_id)
            self._ensure_account(connection, recipient_id)
            sender_balance = connection.execute(
                "SELECT balance FROM gem_accounts WHERE user_id = ?",
                (sender_id,),
            ).fetchone()[0]
            if sender_balance < amount:
                return False, int(sender_balance)

            connection.execute(
                "UPDATE gem_accounts SET balance = balance - ? WHERE user_id = ?",
                (amount, sender_id),
            )
            connection.execute(
                "UPDATE gem_accounts SET balance = balance + ? WHERE user_id = ?",
                (amount, recipient_id),
            )
            remaining = int(sender_balance) - amount
        return True, remaining

    async def transfer(
        self, sender_id: int, recipient_id: int, amount: int
    ) -> Tuple[bool, int]:
        return await asyncio.to_thread(self._transfer, sender_id, recipient_id, amount)

    def _place_bet(self, user_id: int, amount: int) -> Tuple[bool, int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            balance = int(
                connection.execute(
                    "SELECT balance FROM gem_accounts WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
            )
            if balance < amount:
                return False, balance
            connection.execute(
                "UPDATE gem_accounts SET balance = balance - ? WHERE user_id = ?",
                (amount, user_id),
            )
        return True, balance - amount

    async def place_bet(self, user_id: int, amount: int) -> Tuple[bool, int]:
        return await asyncio.to_thread(self._place_bet, user_id, amount)

    def _settle_game(self, user_id: int, payout: int, xp_earned: int) -> GemAccount:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            connection.execute(
                """
                UPDATE gem_accounts
                SET balance = balance + ?, xp = xp + ?
                WHERE user_id = ?
                """,
                (payout, xp_earned, user_id),
            )
            row = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return GemAccount(user_id, int(row[0]), int(row[1]))

    async def settle_game(
        self, user_id: int, payout: int, xp_earned: int
    ) -> GemAccount:
        return await asyncio.to_thread(self._settle_game, user_id, payout, xp_earned)

    def _refund(self, user_id: int, amount: int) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            connection.execute(
                "UPDATE gem_accounts SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id),
            )

    async def refund(self, user_id: int, amount: int) -> None:
        await asyncio.to_thread(self._refund, user_id, amount)

    def _play_slots(
        self, user_id: int, bet: int, payout: int, xp_earned: int
    ) -> Tuple[bool, Optional[GemAccount], int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            row = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            balance, current_xp = int(row[0]), int(row[1])
            if balance < bet:
                return False, GemAccount(user_id, balance, current_xp), 0

            credited_payout = min(payout, MAX_SQLITE_INTEGER - (balance - bet))
            account_xp = current_xp + xp_earned
            account_xp = min(account_xp, MAX_SQLITE_INTEGER)
            applied_xp = account_xp - current_xp
            connection.execute(
                """
                UPDATE gem_accounts
                SET balance = balance - ? + ?, xp = xp + ?
                WHERE user_id = ?
                """,
                (bet, credited_payout, applied_xp, user_id),
            )
            updated = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return (
            True,
            GemAccount(user_id, int(updated[0]), int(updated[1])),
            credited_payout,
        )

    async def play_slots(
        self, user_id: int, bet: int, payout: int, xp_earned: int
    ) -> Tuple[bool, Optional[GemAccount], int]:
        return await asyncio.to_thread(
            self._play_slots, user_id, bet, payout, xp_earned
        )

    def _claim_daily(self, user_id: int) -> Tuple[str, GemAccount, int]:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            row = connection.execute(
                """
                SELECT gem_accounts.balance, gem_accounts.xp,
                       daily_gem_claims.claimed_at
                FROM gem_accounts
                LEFT JOIN daily_gem_claims USING (user_id)
                WHERE gem_accounts.user_id = ?
                """,
                (user_id,),
            ).fetchone()
            balance, xp, last_claim = int(row[0]), int(row[1]), row[2]

            if last_claim is not None:
                seconds_remaining = DAILY_CLAIM_SECONDS - (now - int(last_claim))
                if seconds_remaining > 0:
                    return (
                        "cooldown",
                        GemAccount(user_id, balance, xp),
                        seconds_remaining,
                    )

            if balance > MAX_SQLITE_INTEGER - DAILY_CLAIM_GEMS:
                return "capacity", GemAccount(user_id, balance, xp), 0

            connection.execute(
                "UPDATE gem_accounts SET balance = balance + ? WHERE user_id = ?",
                (DAILY_CLAIM_GEMS, user_id),
            )
            connection.execute(
                """
                INSERT INTO daily_gem_claims (user_id, claimed_at)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET claimed_at = excluded.claimed_at
                """,
                (user_id, now),
            )
            new_balance = balance + DAILY_CLAIM_GEMS

        return "claimed", GemAccount(user_id, new_balance, xp), 0

    async def claim_daily(self, user_id: int) -> Tuple[str, GemAccount, int]:
        return await asyncio.to_thread(self._claim_daily, user_id)

    def _reserve_multiplayer_stake(
        self, match_id: str, player_one: int, player_two: int, stake: int
    ) -> Tuple[bool, int, int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, player_one)
            self._ensure_account(connection, player_two)
            rows = connection.execute(
                """
                SELECT user_id, balance FROM gem_accounts
                WHERE user_id IN (?, ?)
                """,
                (player_one, player_two),
            ).fetchall()
            balances = {int(user_id): int(balance) for user_id, balance in rows}
            balance_one = balances[player_one]
            balance_two = balances[player_two]
            if balance_one < stake or balance_two < stake:
                return False, balance_one, balance_two

            connection.execute(
                "UPDATE gem_accounts SET balance = balance - ? WHERE user_id IN (?, ?)",
                (stake, player_one, player_two),
            )
            connection.execute(
                """
                INSERT INTO multiplayer_escrows
                    (match_id, player_one, player_two, stake, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (match_id, player_one, player_two, stake),
            )
        return True, balance_one - stake, balance_two - stake

    async def reserve_multiplayer_stake(
        self, match_id: str, player_one: int, player_two: int, stake: int
    ) -> Tuple[bool, int, int]:
        return await asyncio.to_thread(
            self._reserve_multiplayer_stake,
            match_id,
            player_one,
            player_two,
            stake,
        )

    def _settle_multiplayer_match(
        self, match_id: str, winner_id: Optional[int]
    ) -> Tuple[bool, Optional[GemAccount], Optional[GemAccount], int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            match = connection.execute(
                """
                SELECT player_one, player_two, stake, status
                FROM multiplayer_escrows WHERE match_id = ?
                """,
                (match_id,),
            ).fetchone()
            if match is None:
                return False, None, None, 0

            player_one, player_two, stake, status = (
                int(match[0]),
                int(match[1]),
                int(match[2]),
                str(match[3]),
            )
            if status != "pending":
                return False, None, None, 0
            if winner_id not in (None, player_one, player_two):
                raise ValueError("Winner must be one of the escrowed players.")

            credited_pot = 0
            if winner_id is None:
                connection.execute(
                    """
                    UPDATE gem_accounts SET balance = balance + ?
                    WHERE user_id IN (?, ?)
                    """,
                    (stake, player_one, player_two),
                )
            else:
                balance_row = connection.execute(
                    "SELECT balance FROM gem_accounts WHERE user_id = ?",
                    (winner_id,),
                ).fetchone()
                current_balance = int(balance_row[0])
                credited_pot = min(
                    stake * 2, MAX_SQLITE_INTEGER - current_balance
                )
                connection.execute(
                    """
                    UPDATE gem_accounts
                    SET balance = balance + ?, xp = MIN(xp + 20, ?)
                    WHERE user_id = ?
                    """,
                    (credited_pot, MAX_SQLITE_INTEGER, winner_id),
                )

            connection.execute(
                "UPDATE multiplayer_escrows SET status = 'settled' WHERE match_id = ?",
                (match_id,),
            )
            accounts = connection.execute(
                """
                SELECT user_id, balance, xp FROM gem_accounts
                WHERE user_id IN (?, ?)
                """,
                (player_one, player_two),
            ).fetchall()
            by_id = {
                int(user_id): GemAccount(int(user_id), int(balance), int(xp))
                for user_id, balance, xp in accounts
            }

        return True, by_id[player_one], by_id[player_two], credited_pot

    async def settle_multiplayer_match(
        self, match_id: str, winner_id: Optional[int]
    ) -> Tuple[bool, Optional[GemAccount], Optional[GemAccount], int]:
        return await asyncio.to_thread(
            self._settle_multiplayer_match, match_id, winner_id
        )

    def _award_xp(self, user_id: int, xp: int) -> GemAccount:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            connection.execute(
                "UPDATE gem_accounts SET xp = MIN(xp + ?, ?) WHERE user_id = ?",
                (xp, MAX_SQLITE_INTEGER, user_id),
            )
            row = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return GemAccount(user_id, int(row[0]), int(row[1]))

    async def award_xp(self, user_id: int, xp: int) -> GemAccount:
        return await asyncio.to_thread(self._award_xp, user_id, xp)

    def _reserve_ai_stake(self, match_id: str, user_id: int, stake: int) -> Tuple[bool, int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection, user_id)
            balance = int(
                connection.execute(
                    "SELECT balance FROM gem_accounts WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
            )
            if balance < stake:
                return False, balance

            connection.execute(
                "UPDATE gem_accounts SET balance = balance - ? WHERE user_id = ?",
                (stake, user_id),
            )
            connection.execute(
                """
                INSERT INTO ai_game_escrows (match_id, user_id, stake, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (match_id, user_id, stake),
            )
        return True, balance - stake

    async def reserve_ai_stake(
        self, match_id: str, user_id: int, stake: int
    ) -> Tuple[bool, int]:
        return await asyncio.to_thread(
            self._reserve_ai_stake, match_id, user_id, stake
        )

    def _settle_ai_match(
        self, match_id: str, outcome: str, xp_earned: int
    ) -> Tuple[bool, Optional[GemAccount], int]:
        if outcome not in ("win", "loss", "draw", "cancel"):
            raise ValueError("Outcome must be win, loss, draw, or cancel.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            escrow = connection.execute(
                "SELECT user_id, stake, status FROM ai_game_escrows WHERE match_id = ?",
                (match_id,),
            ).fetchone()
            if escrow is None or str(escrow[2]) != "pending":
                return False, None, 0

            user_id, stake = int(escrow[0]), int(escrow[1])
            account_row = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            balance, xp = int(account_row[0]), int(account_row[1])

            payout = 0
            if outcome in ("draw", "cancel"):
                payout = stake
            elif outcome == "win":
                payout = min(stake * 2, MAX_SQLITE_INTEGER - balance)
                xp_earned += 20

            updated_xp = min(xp + xp_earned, MAX_SQLITE_INTEGER)
            connection.execute(
                """
                UPDATE gem_accounts SET balance = balance + ?, xp = ?
                WHERE user_id = ?
                """,
                (payout, updated_xp, user_id),
            )
            connection.execute(
                "UPDATE ai_game_escrows SET status = 'settled' WHERE match_id = ?",
                (match_id,),
            )
            updated = connection.execute(
                "SELECT balance, xp FROM gem_accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        return True, GemAccount(user_id, int(updated[0]), int(updated[1])), payout

    async def settle_ai_match(
        self, match_id: str, outcome: str, xp_earned: int
    ) -> Tuple[bool, Optional[GemAccount], int]:
        return await asyncio.to_thread(
            self._settle_ai_match, match_id, outcome, xp_earned
        )
