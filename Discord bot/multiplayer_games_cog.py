import asyncio
import random
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import discord
from discord.ext import commands

from gem_store import GemAccount, GemStore, MAX_SQLITE_INTEGER


ANIMALS: Tuple[Tuple[str, str, str], ...] = (
    ("🐯", "Tiger", "ខ្លា"),
    ("🟢", "Gourd", "ឃ្លោក"),
    ("🐟", "Fish", "ត្រី"),
    ("🦀", "Crab", "ក្តាម"),
    ("🦐", "Shrimp", "បង្គា"),
    ("🐓", "Rooster", "មាន់"),
)
GRID_SIZES: Tuple[int, ...] = (3, 5, 6)
CONNECT_NEED = {3: 3, 5: 4, 6: 4}
BATTLESHIP_LENGTHS = {3: (2,), 5: (3, 2), 6: (4, 3, 2)}
WIN_XP = 20
DRAW_XP = 10
ARENA_COLOR = discord.Color.from_rgb(94, 72, 190)
TTT_COLOR = discord.Color.from_rgb(77, 118, 220)
KLOK_COLOR = discord.Color.from_rgb(40, 130, 105)
NAVY_COLOR = discord.Color.from_rgb(28, 72, 128)
GOLD_COLOR = discord.Color.gold()
MUTED_COLOR = discord.Color.from_rgb(72, 78, 92)


def premium_embed(
    title: str, description: str, color: discord.Color
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="SAD BOT  •  MULTIPLAYER ARENA")
    return embed


def disable_children(view: discord.ui.View) -> None:
    for child in view.children:
        child.disabled = True


async def safe_edit(
    message: Optional[discord.Message], **kwargs
) -> None:
    if message is None:
        return
    try:
        await message.edit(**kwargs)
    except discord.HTTPException:
        return


def account_balance(
    first: Optional[GemAccount], second: Optional[GemAccount], user_id: int
) -> Optional[int]:
    for account in (first, second):
        if account is not None and account.user_id == user_id:
            return account.balance
    return None


def winning_lines(size: int, need: int) -> Tuple[Tuple[int, ...], ...]:
    lines: List[Tuple[int, ...]] = []
    for row in range(size):
        for col in range(size - need + 1):
            start = row * size + col
            lines.append(tuple(start + offset for offset in range(need)))
    for col in range(size):
        for row in range(size - need + 1):
            lines.append(
                tuple((row + offset) * size + col for offset in range(need))
            )
    for row in range(size - need + 1):
        for col in range(size - need + 1):
            lines.append(
                tuple((row + offset) * size + col + offset for offset in range(need))
            )
            lines.append(
                tuple(
                    (row + offset) * size + col + need - 1 - offset
                    for offset in range(need)
                )
            )
    return tuple(lines)


def line_winner(
    board: Sequence[Optional[str]], lines: Sequence[Sequence[int]]
) -> Optional[str]:
    for line in lines:
        mark = board[line[0]]
        if mark is not None and all(board[index] == mark for index in line):
            return mark
    return None


def grid_label(index: int, size: int) -> str:
    return f"{chr(65 + index // size)}{index % size + 1}"


def render_marked_board(board: Sequence[Optional[str]], size: int) -> str:
    header = "   " + "".join(f"{column:>3}" for column in range(1, size + 1))
    rows = [header]
    for row in range(size):
        cells = []
        for column in range(size):
            mark = board[row * size + column]
            cells.append(f"{(mark or '·'):>3}")
        rows.append(f"{chr(65 + row)} " + "".join(cells))
    return "```\n" + "\n".join(rows) + "\n```"


def render_battle_grid(
    size: int,
    *,
    ships: Set[int],
    hits: Set[int],
    misses: Set[int],
    reveal_ships: bool,
) -> str:
    header = "   " + "".join(f"{column:>3}" for column in range(1, size + 1))
    rows = [header]
    for row in range(size):
        cells = []
        for column in range(size):
            index = row * size + column
            if index in hits:
                symbol = "#" if index in ships else "x"
            elif index in misses:
                symbol = "o"
            elif reveal_ships and index in ships:
                symbol = "S"
            else:
                symbol = "·"
            cells.append(f"{symbol:>3}")
        rows.append(f"{chr(65 + row)} " + "".join(cells))
    return "```\n" + "\n".join(rows) + "\n```"


def ttt_ai_move(
    board: List[Optional[str]],
    size: int,
    lines: Sequence[Sequence[int]],
    ai_mark: str,
    human_mark: str,
) -> int:
    empties = [index for index, mark in enumerate(board) if mark is None]

    def winning_square(mark: str) -> Optional[int]:
        for index in empties:
            board[index] = mark
            won = line_winner(board, lines) == mark
            board[index] = None
            if won:
                return index
        return None

    if random.random() < 0.38:
        return random.choice(empties)

    winning = winning_square(ai_mark)
    if winning is not None:
        return winning

    blocking = winning_square(human_mark)
    if blocking is not None and random.random() < 0.78:
        return blocking

    if size % 2 == 1:
        center = (size * size) // 2
        if board[center] is None:
            return center

    corners = [
        0,
        size - 1,
        size * (size - 1),
        size * size - 1,
    ]
    open_corners = [index for index in corners if board[index] is None]
    if open_corners and random.random() < 0.55:
        return random.choice(open_corners)
    return random.choice(empties)


def place_fleet(size: int, lengths: Sequence[int]) -> List[Set[int]]:
    for _ in range(80):
        occupied: Set[int] = set()
        ships: List[Set[int]] = []
        failed = False
        for length in lengths:
            placed: Optional[Set[int]] = None
            for _attempt in range(120):
                horizontal = random.choice((True, False))
                if horizontal:
                    row = random.randrange(size)
                    column = random.randrange(size - length + 1)
                    cells = {row * size + column + offset for offset in range(length)}
                else:
                    row = random.randrange(size - length + 1)
                    column = random.randrange(size)
                    cells = {
                        (row + offset) * size + column for offset in range(length)
                    }
                if cells & occupied:
                    continue
                placed = cells
                break
            if placed is None:
                failed = True
                break
            occupied |= placed
            ships.append(placed)
        if not failed:
            return ships
    raise RuntimeError("Unable to place a valid fleet.")


class Fleet:
    def __init__(self, size: int, lengths: Sequence[int]) -> None:
        self.size = size
        self.ships = place_fleet(size, lengths)
        self.hits: Set[int] = set()
        self.misses: Set[int] = set()

    @property
    def ship_cells(self) -> Set[int]:
        cells: Set[int] = set()
        for ship in self.ships:
            cells |= ship
        return cells

    @property
    def sunk_cells(self) -> Set[int]:
        cells: Set[int] = set()
        for ship in self.ships:
            if ship <= self.hits:
                cells |= ship
        return cells

    def remaining_ships(self) -> int:
        return sum(1 for ship in self.ships if not ship <= self.hits)

    def already_fired(self, index: int) -> bool:
        return index in self.hits or index in self.misses

    def fire(self, index: int) -> str:
        if index in self.ship_cells:
            self.hits.add(index)
            for ship in self.ships:
                if index in ship and ship <= self.hits:
                    return "sunk"
            return "hit"
        self.misses.add(index)
        return "miss"

    def defeated(self) -> bool:
        return self.remaining_ships() == 0


def battleship_ai_shot(fleet: Fleet) -> int:
    unknown = [
        index
        for index in range(fleet.size * fleet.size)
        if not fleet.already_fired(index)
    ]
    unsunk_hits = [index for index in fleet.hits if index not in fleet.sunk_cells]
    targets: List[int] = []
    for hit in unsunk_hits:
        row, column = divmod(hit, fleet.size)
        neighbors = (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        )
        for next_row, next_column in neighbors:
            if 0 <= next_row < fleet.size and 0 <= next_column < fleet.size:
                index = next_row * fleet.size + next_column
                if not fleet.already_fired(index):
                    targets.append(index)
    if targets and random.random() < 0.72:
        return random.choice(targets)
    return random.choice(unknown)


@dataclass
class MatchSession:
    host: discord.Member
    opponent: discord.Member
    is_ai: bool
    store: GemStore
    stake: int = 0
    match_id: Optional[str] = None
    reserved: bool = False
    settled: bool = False
    game_key: str = ""
    grid_size: int = 3
    bet_chosen: bool = False
    launched: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def mention_pair(self) -> str:
        if self.is_ai:
            return (
                f"**{self.host.mention}**  vs  **{self.opponent.mention}**"
                "  •  AI Mode"
            )
        return f"**{self.host.mention}**  vs  **{self.opponent.mention}**"

    def stake_line(self) -> str:
        if self.stake <= 0:
            return "Free Play  •  no Gems at risk"
        if self.is_ai:
            return f"Wager  •  `{self.stake:,} Gems` against SadBot"
        return f"Wager  •  `{self.stake:,} Gems` from each player"

    def is_participant(self, user_id: int) -> bool:
        return user_id in (self.host.id, self.opponent.id)

    async def reserve(self) -> Tuple[bool, Optional[discord.Embed]]:
        if self.stake <= 0:
            return True, None
        self.match_id = uuid.uuid4().hex
        if self.is_ai:
            reserved, balance = await self.store.reserve_ai_stake(
                self.match_id, self.host.id, self.stake
            )
            if not reserved:
                self.match_id = None
                return False, premium_embed(
                    "INSUFFICIENT GEMS",
                    f"AI Wager requires **`{self.stake:,} Gems`**.\n"
                    f"Your balance: `{balance:,} Gems`.",
                    discord.Color.red(),
                )
            self.reserved = True
            return True, None

        reserved, host_balance, opponent_balance = (
            await self.store.reserve_multiplayer_stake(
                self.match_id,
                self.host.id,
                self.opponent.id,
                self.stake,
            )
        )
        if not reserved:
            self.match_id = None
            return False, premium_embed(
                "INSUFFICIENT GEMS",
                f"Wager Mode requires **`{self.stake:,} Gems`** from each player.\n\n"
                f"**{self.host.display_name}:** `{host_balance:,} Gems`\n"
                f"**{self.opponent.display_name}:** `{opponent_balance:,} Gems`",
                discord.Color.red(),
            )
        self.reserved = True
        return True, None

    async def settle(
        self, winner_id: Optional[int], *, cancelled: bool = False
    ) -> Tuple[Optional[GemAccount], Optional[GemAccount], int]:
        if self.settled:
            return None, None, 0

        if not self.reserved or self.stake <= 0 or self.match_id is None:
            if cancelled:
                self.settled = True
                return None, None, 0
            if self.is_ai:
                if winner_id == self.host.id:
                    await self.store.award_xp(self.host.id, WIN_XP)
                elif winner_id is None:
                    await self.store.award_xp(self.host.id, DRAW_XP)
            else:
                if winner_id is None:
                    await asyncio.gather(
                        self.store.award_xp(self.host.id, DRAW_XP),
                        self.store.award_xp(self.opponent.id, DRAW_XP),
                    )
                else:
                    await self.store.award_xp(winner_id, WIN_XP)
            self.settled = True
            return None, None, 0

        if self.is_ai:
            if cancelled:
                outcome = "cancel"
                xp_earned = 0
            elif winner_id is None:
                outcome = "draw"
                xp_earned = DRAW_XP
            elif winner_id == self.host.id:
                outcome = "win"
                xp_earned = 0
            else:
                outcome = "loss"
                xp_earned = 0
            settled, account, payout = await self.store.settle_ai_match(
                self.match_id, outcome, xp_earned
            )
            self.settled = True
            if not settled:
                return None, None, 0
            return account, None, payout

        settled, first, second, pot = await self.store.settle_multiplayer_match(
            self.match_id, None if cancelled else winner_id
        )
        self.settled = True
        if not settled:
            return None, None, 0
        if not cancelled and winner_id is None:
            await asyncio.gather(
                self.store.award_xp(self.host.id, DRAW_XP),
                self.store.award_xp(self.opponent.id, DRAW_XP),
            )
        return first, second, pot


def wager_summary(session: MatchSession) -> str:
    return (
        f"{session.mention_pair()}\n"
        f"{session.stake_line()}"
    )


async def launch_match(
    interaction: discord.Interaction, session: MatchSession
) -> None:
    if session.launched:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "The match is already starting.",
                ephemeral=True,
            )
        return
    session.launched = True
    try:
        reserved, error_embed = await session.reserve()
    except sqlite3.Error:
        session.launched = False
        await interaction.response.send_message(
            "The Gem Vault is temporarily unavailable. No Gems were taken.",
            ephemeral=True,
        )
        return
    if not reserved and error_embed is not None:
        session.launched = False
        await interaction.response.edit_message(embed=error_embed, view=None)
        return

    if session.game_key == "ttt":
        view: discord.ui.View = TicTacToeView(session)
    elif session.game_key == "klok":
        view = KhlaKlokView(session)
    else:
        view = BattleshipView(session)
    view.message = interaction.message  # type: ignore[attr-defined]
    await interaction.response.edit_message(
        embed=view.build_embed(),  # type: ignore[attr-defined]
        view=view,
    )


class BetModeView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=120)
        self.session = session
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.host.id:
            await interaction.response.send_message(
                "Only the host can choose the match mode.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        disable_children(self)
        await safe_edit(
            self.message,
            embed=premium_embed(
                "CHALLENGE EXPIRED",
                "The host did not choose Free Play or Wager Mode in time.",
                MUTED_COLOR,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Free Play",
        style=discord.ButtonStyle.primary,
        emoji="🎮",
    )
    async def free_play(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.session.bet_chosen:
            await interaction.response.send_message(
                "Match mode is already set.",
                ephemeral=True,
            )
            return
        self.session.bet_chosen = True
        self.session.stake = 0
        await continue_after_bet(interaction, self.session)
        self.stop()

    @discord.ui.button(
        label="Gem Wager",
        style=discord.ButtonStyle.success,
        emoji="💎",
    )
    async def gem_wager(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(WagerModal(self.session, self))


class WagerModal(discord.ui.Modal, title="Gem Wager"):
    amount = discord.ui.TextInput(
        label="Wager amount in Gems",
        placeholder="Enter a whole number, for example 100",
        min_length=1,
        max_length=19,
        required=True,
    )

    def __init__(self, session: MatchSession, origin: BetModeView) -> None:
        super().__init__()
        self.session = session
        self.origin = origin

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw = str(self.amount.value).replace(",", "").strip()
        try:
            stake = int(raw)
        except ValueError:
            await interaction.response.send_message(
                "Enter a positive whole number of Gems.",
                ephemeral=True,
            )
            return
        if stake <= 0 or stake > MAX_SQLITE_INTEGER // 2:
            await interaction.response.send_message(
                "Choose a positive wager within the supported Gem limit.",
                ephemeral=True,
            )
            return
        try:
            account = await self.session.store.get_account(self.session.host.id)
        except sqlite3.Error:
            await interaction.response.send_message(
                "The Gem Vault is temporarily unavailable.",
                ephemeral=True,
            )
            return
        if account.balance < stake:
            await interaction.response.send_message(
                f"You need `{stake:,} Gems` for this wager. "
                f"Your balance is `{account.balance:,} Gems`.",
                ephemeral=True,
            )
            return
        if self.session.bet_chosen:
            await interaction.response.send_message(
                "Match mode is already set.",
                ephemeral=True,
            )
            return
        self.session.bet_chosen = True
        self.session.stake = stake
        await continue_after_bet(interaction, self.session)
        self.origin.stop()


async def continue_after_bet(
    interaction: discord.Interaction, session: MatchSession
) -> None:
    if session.is_ai:
        view = GameSelectView(session)
        view.message = interaction.message
        embed = premium_embed(
            "SELECT A GAME",
            f"{wager_summary(session)}\n\n"
            "Choose Tic-Tac-Toe, Khla Klok, or Battleship. "
            "Grid games include 3×3, 5×5, and 6×6 boards.",
            ARENA_COLOR,
        )
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.edit_message(embed=embed, view=view)
        return

    view = ChallengeView(session)
    view.message = interaction.message
    embed = premium_embed(
        "MATCH INVITATION",
        f"**{session.host.mention}** challenged **{session.opponent.mention}**.\n\n"
        f"{session.stake_line()}\n"
        "The invited player may accept or decline.",
        ARENA_COLOR,
    )
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)


class ChallengeView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=120)
        self.session = session
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.opponent.id:
            await interaction.response.send_message(
                "This invitation is for the challenged player only.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        disable_children(self)
        await safe_edit(
            self.message,
            embed=premium_embed(
                "INVITATION EXPIRED",
                "The challenged player did not respond in time.",
                MUTED_COLOR,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="⚔️",
    )
    async def accept(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.session.stake > 0:
            try:
                account = await self.session.store.get_account(
                    self.session.opponent.id
                )
            except sqlite3.Error:
                await interaction.response.send_message(
                    "The Gem Vault is temporarily unavailable.",
                    ephemeral=True,
                )
                return
            if account.balance < self.session.stake:
                await interaction.response.send_message(
                    f"You need `{self.session.stake:,} Gems` to accept this wager. "
                    f"Your balance is `{account.balance:,} Gems`.",
                    ephemeral=True,
                )
                return
        view = GameSelectView(self.session)
        view.message = interaction.message
        embed = premium_embed(
            "SELECT A GAME",
            f"{wager_summary(self.session)}\n\n"
            f"**{self.session.host.mention}** chooses the mini-game.",
            ARENA_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=view)
        self.stop()

    @discord.ui.button(
        label="Decline",
        style=discord.ButtonStyle.secondary,
        emoji="✖️",
    )
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        disable_children(self)
        embed = premium_embed(
            "CHALLENGE DECLINED",
            f"{self.session.opponent.mention} declined the invitation.",
            MUTED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class GameSelectView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=120)
        self.session = session
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.host.id:
            await interaction.response.send_message(
                "Only the host can select the mini-game.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        disable_children(self)
        await safe_edit(
            self.message,
            embed=premium_embed(
                "SELECTION EXPIRED",
                "No mini-game was selected in time.",
                MUTED_COLOR,
            ),
            view=self,
        )

    async def pick_grid_game(
        self, interaction: discord.Interaction, game_key: str, title: str, blurb: str
    ) -> None:
        self.session.game_key = game_key
        view = GridSizeView(self.session)
        view.message = interaction.message
        embed = premium_embed(
            title,
            f"{wager_summary(self.session)}\n\n{blurb}",
            ARENA_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=view)
        self.stop()

    @discord.ui.button(
        label="Tic-Tac-Toe",
        style=discord.ButtonStyle.primary,
        emoji="❎",
        row=0,
    )
    async def tic_tac_toe(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.pick_grid_game(
            interaction,
            "ttt",
            "TIC-TAC-TOE  •  BOARD SIZE",
            "Choose a board. 3×3 wins with 3 in a row. "
            "5×5 and 6×6 win with 4 in a row.",
        )

    @discord.ui.button(
        label="Khla Klok",
        style=discord.ButtonStyle.success,
        emoji="🐯",
        row=0,
    )
    async def khla_klok(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.session.game_key = "klok"
        await launch_match(interaction, self.session)
        self.stop()

    @discord.ui.button(
        label="Battleship",
        style=discord.ButtonStyle.secondary,
        emoji="🚢",
        row=0,
    )
    async def battleship(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.pick_grid_game(
            interaction,
            "ship",
            "BATTLESHIP  •  GRID SIZE",
            "Choose a naval grid. Fleets are placed automatically. "
            "Sink every opposing ship to win.",
        )


class GridSizeView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=120)
        self.session = session
        self.message: Optional[discord.Message] = None
        labels = {
            3: ("3 × 3", "Classic"),
            5: ("5 × 5", "Advanced"),
            6: ("6 × 6", "Grandmaster"),
        }
        styles = {
            3: discord.ButtonStyle.primary,
            5: discord.ButtonStyle.success,
            6: discord.ButtonStyle.secondary,
        }
        for size in GRID_SIZES:
            self.add_item(
                GridSizeButton(size, labels[size][0], labels[size][1], styles[size])
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.host.id:
            await interaction.response.send_message(
                "Only the host can choose the grid size.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        disable_children(self)
        await safe_edit(
            self.message,
            embed=premium_embed(
                "SELECTION EXPIRED",
                "No grid size was selected in time.",
                MUTED_COLOR,
            ),
            view=self,
        )

    async def choose(self, interaction: discord.Interaction, size: int) -> None:
        self.session.grid_size = size
        await launch_match(interaction, self.session)
        self.stop()


class GridSizeButton(discord.ui.Button):
    def __init__(
        self,
        size: int,
        label: str,
        extra: str,
        style: discord.ButtonStyle,
    ) -> None:
        super().__init__(label=f"{label}  {extra}", style=style, row=0)
        self.size = size

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, GridSizeView):
            await self.view.choose(interaction, self.size)


class CoordinateSelect(discord.ui.Select):
    def __init__(self, kind: str, size: int) -> None:
        self.kind = kind
        if kind == "row":
            options = [
                discord.SelectOption(label=chr(65 + index), value=str(index))
                for index in range(size)
            ]
            placeholder = "Select row"
        else:
            options = [
                discord.SelectOption(label=str(index + 1), value=str(index))
                for index in range(size)
            ]
            placeholder = "Select column"
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=0 if kind == "row" else 1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, (TicTacToeView, BattleshipView)):
            return
        value = int(self.values[0])
        if self.kind == "row":
            view.selected_row = value
        else:
            view.selected_col = value
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class CoordinateActionButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str) -> None:
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.success,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if isinstance(view, TicTacToeView):
            if view.selected_row is None or view.selected_col is None:
                await interaction.response.send_message(
                    "Select a row and a column first.",
                    ephemeral=True,
                )
                return
            await view.play(
                interaction, view.selected_row * view.size + view.selected_col
            )
        elif isinstance(view, BattleshipView):
            if view.selected_row is None or view.selected_col is None:
                await interaction.response.send_message(
                    "Select a row and a column first.",
                    ephemeral=True,
                )
                return
            await view.fire(
                interaction, view.selected_row * view.size + view.selected_col
            )


class TicTacToeView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=300)
        self.session = session
        self.size = session.grid_size
        self.need = CONNECT_NEED[self.size]
        self.lines = winning_lines(self.size, self.need)
        self.player_x = session.host
        self.player_o = session.opponent
        self.current_player_id = session.host.id
        self.board: List[Optional[str]] = [None] * (self.size * self.size)
        self.game_over = False
        self.message: Optional[discord.Message] = None
        self.selected_row: Optional[int] = None
        self.selected_col: Optional[int] = None
        self.use_console = self.size >= 6
        if self.use_console:
            self.add_item(CoordinateSelect("row", self.size))
            self.add_item(CoordinateSelect("column", self.size))
            self.add_item(CoordinateActionButton("Place Mark", "📌"))
        else:
            for index in range(self.size * self.size):
                self.add_item(TicTacToeButton(index, self.size))

    def player_for(self, mark: str) -> discord.Member:
        return self.player_x if mark == "X" else self.player_o

    def mark_for(self, user_id: int) -> str:
        return "X" if user_id == self.player_x.id else "O"

    def build_embed(self, note: Optional[str] = None) -> discord.Embed:
        next_mark = self.mark_for(self.current_player_id)
        actor = self.player_for(next_mark)
        description = note or f"{self.session.mention_pair()}\n{self.session.stake_line()}"
        if self.use_console and self.selected_row is not None and self.selected_col is not None:
            description += (
                f"\nTarget locked: **{chr(65 + self.selected_row)}"
                f"{self.selected_col + 1}**"
            )
        embed = premium_embed("TIC-TAC-TOE", description, TTT_COLOR)
        embed.add_field(
            name=f"BOARD  •  {self.size}×{self.size}  •  CONNECT {self.need}",
            value=render_marked_board(self.board, self.size),
            inline=False,
        )
        embed.add_field(
            name="TURN",
            value=f"**{actor.mention}**  •  `{next_mark}`",
            inline=False,
        )
        embed.set_footer(text="SAD BOT  •  TIC-TAC-TOE")
        return embed

    def apply_mark(self, index: int, mark: str) -> None:
        self.board[index] = mark
        if not self.use_console:
            button = self.children[index]
            if isinstance(button, discord.ui.Button):
                button.label = mark
                button.style = (
                    discord.ButtonStyle.primary
                    if mark == "X"
                    else discord.ButtonStyle.success
                )
                button.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.player_x.id, self.player_o.id):
            await interaction.response.send_message(
                "Only the two match players can place a mark.",
                ephemeral=True,
            )
            return False
        if self.session.is_ai and interaction.user.id == self.player_o.id:
            return False
        if interaction.user.id != self.current_player_id:
            await interaction.response.send_message(
                "It is the other player's turn.",
                ephemeral=True,
            )
            return False
        return True

    async def finish(
        self,
        interaction: Optional[discord.Interaction],
        winner: Optional[str],
        use_response: bool,
    ) -> None:
        self.game_over = True
        disable_children(self)
        winner_id = None if winner is None else self.player_for(winner).id
        try:
            first, second, pot = await self.session.settle(winner_id)
        except sqlite3.Error:
            embed = premium_embed(
                "VAULT ERROR",
                "The match ended, but the Gem Vault could not finish settlement.",
                discord.Color.red(),
            )
            if use_response and interaction is not None:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await safe_edit(self.message, embed=embed, view=self)
            self.stop()
            return

        if winner is None:
            title = "MATCH DRAW"
            result = "The board is full with no connecting line. Stakes are returned."
            if self.session.stake <= 0:
                result = "The board is full with no connecting line. Both sides earn draw XP."
            color = discord.Color.blurple()
        else:
            champion = self.player_for(winner)
            title = "VICTORY"
            if self.session.stake > 0:
                result = (
                    f"**{champion.mention}** wins with `{winner}` and receives "
                    f"**`{pot:,} Gems`**."
                )
            else:
                result = f"**{champion.mention}** wins with `{winner}` and earns match XP."
            color = GOLD_COLOR

        embed = premium_embed(title, result, color)
        embed.add_field(
            name="FINAL BOARD",
            value=render_marked_board(self.board, self.size),
            inline=False,
        )
        if first is not None:
            host_balance = account_balance(first, second, self.session.host.id)
            if host_balance is not None:
                embed.add_field(
                    name="GEM BALANCE",
                    value=f"**{self.session.host.display_name}:** `{host_balance:,} Gems`",
                    inline=False,
                )
        embed.set_footer(text="SAD BOT  •  TIC-TAC-TOE")
        if use_response and interaction is not None:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await safe_edit(self.message, embed=embed, view=self)
        self.stop()

    async def play(self, interaction: discord.Interaction, index: int) -> None:
        start_ai = False
        async with self.session.lock:
            if self.game_over or self.board[index] is not None:
                await interaction.response.send_message(
                    "That square is no longer available.",
                    ephemeral=True,
                )
                return
            mark = self.mark_for(self.current_player_id)
            self.apply_mark(index, mark)
            winner = line_winner(self.board, self.lines)
            is_draw = winner is None and all(cell is not None for cell in self.board)
            if winner or is_draw:
                await self.finish(interaction, winner, True)
                return
            self.current_player_id = (
                self.player_o.id if mark == "X" else self.player_x.id
            )
            note = (
                f"**{self.player_for(mark).mention}** placed **{mark}** on "
                f"**{grid_label(index, self.size)}**."
            )
            await interaction.response.edit_message(
                embed=self.build_embed(note),
                view=self,
            )
            self.message = interaction.message
            start_ai = self.session.is_ai and not self.game_over
        if start_ai:
            await self.run_ai_turn()

    async def run_ai_turn(self) -> None:
        await asyncio.sleep(random.uniform(0.55, 1.15))
        async with self.session.lock:
            if self.game_over:
                return
            index = ttt_ai_move(self.board, self.size, self.lines, "O", "X")
            self.apply_mark(index, "O")
            winner = line_winner(self.board, self.lines)
            is_draw = winner is None and all(cell is not None for cell in self.board)
            if winner or is_draw:
                await self.finish(None, winner, False)
                return
            self.current_player_id = self.player_x.id
            note = (
                f"**{self.player_o.mention}** placed **O** on "
                f"**{grid_label(index, self.size)}**."
            )
            await safe_edit(self.message, embed=self.build_embed(note), view=self)

    async def on_timeout(self) -> None:
        async with self.session.lock:
            if self.game_over:
                return
            self.game_over = True
            disable_children(self)
            try:
                await self.session.settle(None, cancelled=True)
            except sqlite3.Error:
                await safe_edit(
                    self.message,
                    embed=premium_embed(
                        "STAKE REFUND PENDING",
                        "The match timed out, but the Gem Vault could not refund the wager.",
                        discord.Color.red(),
                    ),
                    view=self,
                )
                return
            await safe_edit(
                self.message,
                embed=premium_embed(
                    "MATCH EXPIRED",
                    "No move was made in time. Any locked Gems have been returned.",
                    MUTED_COLOR,
                ),
                view=self,
            )


class TicTacToeButton(discord.ui.Button):
    def __init__(self, index: int, size: int) -> None:
        super().__init__(
            label=grid_label(index, size),
            style=discord.ButtonStyle.secondary,
            row=index // size,
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, TicTacToeView):
            await self.view.play(interaction, self.index)


class KhlaKlokView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=180)
        self.session = session
        self.players = (session.host, session.opponent)
        self.selections: Dict[int, int] = {}
        self.game_over = False
        self.message: Optional[discord.Message] = None
        if session.is_ai:
            self.selections[session.opponent.id] = random.randrange(len(ANIMALS))
        for index, (emoji, english, khmer) in enumerate(ANIMALS):
            self.add_item(KhlaChoiceButton(index, emoji, english, khmer))

    def build_embed(
        self,
        title: str = "KHLA KLOK",
        description: Optional[str] = None,
        dice: Optional[Sequence[int]] = None,
        balances: Optional[Tuple[Optional[int], Optional[int]]] = None,
        reveal: bool = False,
    ) -> discord.Embed:
        if description is None:
            description = (
                f"{self.session.mention_pair()}\n{self.session.stake_line()}\n\n"
                "Each player selects one symbol. Three dice decide the winner."
            )
        embed = premium_embed(title, description, KLOK_COLOR)
        for index, player in enumerate(self.players):
            selection = self.selections.get(player.id)
            is_ai_hidden = (
                self.session.is_ai
                and player.id == self.session.opponent.id
                and not reveal
            )
            if selection is None:
                selection_text = "Choosing"
            elif is_ai_hidden:
                selection_text = "Ready"
            else:
                emoji, english, khmer = ANIMALS[selection]
                selection_text = f"{emoji}  {english}  {khmer}"
            balance_text = ""
            if balances is not None and balances[index] is not None:
                balance_text = f"\nBalance: `{balances[index]:,} Gems`"
            embed.add_field(
                name=player.display_name,
                value=f"{selection_text}{balance_text}",
                inline=True,
            )
        legend = "   ".join(
            f"{emoji} {english} {khmer}" for emoji, english, khmer in ANIMALS
        )
        embed.add_field(name="TABLE SYMBOLS", value=legend, inline=False)
        if dice is not None:
            dice_text = "   ".join(
                f"{ANIMALS[result][0]} {ANIMALS[result][1]} {ANIMALS[result][2]}"
                for result in dice
            )
            embed.add_field(name="THREE DICE", value=dice_text, inline=False)
        embed.add_field(name="STAKES", value=self.session.stake_line(), inline=False)
        embed.set_footer(text="SAD BOT  •  KHLA KLOK")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (player.id for player in self.players):
            await interaction.response.send_message(
                "Only the two match players can choose a symbol.",
                ephemeral=True,
            )
            return False
        if self.session.is_ai and interaction.user.id == self.session.opponent.id:
            return False
        return True

    async def choose(self, interaction: discord.Interaction, selection: int) -> None:
        async with self.session.lock:
            if self.game_over:
                await interaction.response.send_message(
                    "This Khla Klok round has ended.",
                    ephemeral=True,
                )
                return
            self.selections[interaction.user.id] = selection
            if len(self.selections) < 2:
                embed = self.build_embed(
                    "KHLA KLOK",
                    f"**{interaction.user.mention}** selected "
                    f"**{ANIMALS[selection][1]} {ANIMALS[selection][2]}**.\n"
                    "Waiting for the other player.",
                )
                await interaction.response.edit_message(embed=embed, view=self)
                return

            disable_children(self)
            await interaction.response.edit_message(
                embed=self.build_embed(
                    "KHLA KLOK",
                    "Both symbols are locked. The three dice are rolling.",
                ),
                view=self,
            )
            await asyncio.sleep(1.1)
            dice = [random.randrange(len(ANIMALS)) for _ in range(3)]
            counts = {
                player.id: dice.count(self.selections[player.id])
                for player in self.players
            }
            if counts[self.players[0].id] > counts[self.players[1].id]:
                winner_id: Optional[int] = self.players[0].id
            elif counts[self.players[1].id] > counts[self.players[0].id]:
                winner_id = self.players[1].id
            else:
                winner_id = None

            try:
                first, second, pot = await self.session.settle(winner_id)
            except sqlite3.Error:
                self.selections.pop(interaction.user.id, None)
                self.game_over = False
                for child in self.children:
                    child.disabled = False
                await interaction.edit_original_response(
                    embed=self.build_embed(
                        "KHLA KLOK",
                        "The Gem Vault could not settle this round. Choose again.",
                    ),
                    view=self,
                )
                return

            self.game_over = True
            balances = (
                account_balance(first, second, self.players[0].id),
                account_balance(first, second, self.players[1].id),
            )
            if winner_id is None:
                title = "KHLA KLOK DRAW"
                description = (
                    "Matching dice counts. Locked Gems have been returned."
                    if self.session.stake > 0
                    else "Matching dice counts. Both sides earn draw XP."
                )
            else:
                winner = next(
                    player for player in self.players if player.id == winner_id
                )
                title = "KHLA KLOK VICTORY"
                if self.session.stake > 0:
                    description = (
                        f"**{winner.mention}** wins and receives **`{pot:,} Gems`**."
                    )
                else:
                    description = f"**{winner.mention}** wins the table and earns match XP."

            embed = self.build_embed(
                title,
                description,
                dice,
                balances,
                reveal=True,
            )
            embed.add_field(
                name="DICE COUNTS",
                value="\n".join(
                    f"{player.mention}  •  **{counts[player.id]}**  "
                    f"{ANIMALS[self.selections[player.id]][0]} "
                    f"{ANIMALS[self.selections[player.id]][1]} "
                    f"{ANIMALS[self.selections[player.id]][2]}"
                    for player in self.players
                ),
                inline=False,
            )
            await interaction.edit_original_response(embed=embed, view=self)
            self.stop()

    async def on_timeout(self) -> None:
        async with self.session.lock:
            if self.game_over:
                return
            self.game_over = True
            disable_children(self)
            try:
                first, second, _ = await self.session.settle(None, cancelled=True)
            except sqlite3.Error:
                await safe_edit(
                    self.message,
                    embed=premium_embed(
                        "STAKE REFUND PENDING",
                        "The round timed out, but the Gem Vault could not refund the wager.",
                        discord.Color.red(),
                    ),
                    view=self,
                )
                return
            balances = (
                account_balance(first, second, self.players[0].id),
                account_balance(first, second, self.players[1].id),
            )
            await safe_edit(
                self.message,
                embed=self.build_embed(
                    "KHLA KLOK EXPIRED",
                    "The round timed out. Any locked Gems have been returned.",
                    balances=balances,
                    reveal=True,
                ),
                view=self,
            )


class KhlaChoiceButton(discord.ui.Button):
    def __init__(self, index: int, emoji: str, english: str, khmer: str) -> None:
        super().__init__(
            label=f"{english}  {khmer}",
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            row=index // 3,
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, KhlaKlokView):
            await self.view.choose(interaction, self.index)


class BattleshipView(discord.ui.View):
    def __init__(self, session: MatchSession) -> None:
        super().__init__(timeout=300)
        self.session = session
        self.size = session.grid_size
        self.host_fleet = Fleet(self.size, BATTLESHIP_LENGTHS[self.size])
        self.opponent_fleet = Fleet(self.size, BATTLESHIP_LENGTHS[self.size])
        self.current_player_id = session.host.id
        self.game_over = False
        self.message: Optional[discord.Message] = None
        self.selected_row: Optional[int] = None
        self.selected_col: Optional[int] = None
        self.last_note = (
            f"{session.mention_pair()}\n{session.stake_line()}\n"
            "Fleets are in position. Fire on the opposing grid."
        )
        self.use_console = self.size >= 6
        if self.use_console:
            self.add_item(CoordinateSelect("row", self.size))
            self.add_item(CoordinateSelect("column", self.size))
            self.add_item(CoordinateActionButton("Fire", "🎯"))
        else:
            for index in range(self.size * self.size):
                self.add_item(BattleshipButton(index, self.size))

    def defending_fleet(self, shooter_id: int) -> Fleet:
        if shooter_id == self.session.host.id:
            return self.opponent_fleet
        return self.host_fleet

    def own_fleet(self, user_id: int) -> Fleet:
        if user_id == self.session.host.id:
            return self.host_fleet
        return self.opponent_fleet

    def sync_buttons(self, shooter_id: int) -> None:
        if self.use_console:
            return
        fleet = self.defending_fleet(shooter_id)
        for child in self.children:
            if not isinstance(child, BattleshipButton):
                continue
            index = child.index
            if index in fleet.sunk_cells:
                child.label = "#"
                child.style = discord.ButtonStyle.danger
                child.disabled = True
            elif index in fleet.hits:
                child.label = "x"
                child.style = discord.ButtonStyle.danger
                child.disabled = True
            elif index in fleet.misses:
                child.label = "o"
                child.style = discord.ButtonStyle.secondary
                child.disabled = True
            else:
                child.label = grid_label(index, self.size)
                child.style = discord.ButtonStyle.primary
                child.disabled = self.game_over

    def build_embed(self, note: Optional[str] = None) -> discord.Embed:
        description = note or self.last_note
        current = (
            self.session.host
            if self.current_player_id == self.session.host.id
            else self.session.opponent
        )
        if self.use_console and self.selected_row is not None and self.selected_col is not None:
            description += (
                f"\nTarget locked: **{chr(65 + self.selected_row)}"
                f"{self.selected_col + 1}**"
            )
        embed = premium_embed("BATTLESHIP", description, NAVY_COLOR)
        radar_fleet = self.defending_fleet(self.current_player_id)
        viewer_fleet = self.own_fleet(self.current_player_id)
        if self.session.is_ai:
            radar_fleet = self.opponent_fleet
            viewer_fleet = self.host_fleet
        embed.add_field(
            name=f"RADAR  •  {self.size}×{self.size}",
            value=render_battle_grid(
                self.size,
                ships=radar_fleet.ship_cells,
                hits=radar_fleet.hits,
                misses=radar_fleet.misses,
                reveal_ships=False,
            ),
            inline=False,
        )
        fleet_owner = (
            self.session.host.display_name
            if self.session.is_ai or self.current_player_id == self.session.host.id
            else current.display_name
        )
        embed.add_field(
            name=f"YOUR FLEET  •  {fleet_owner}",
            value=render_battle_grid(
                self.size,
                ships=viewer_fleet.ship_cells,
                hits=viewer_fleet.hits,
                misses=viewer_fleet.misses,
                reveal_ships=True,
            ),
            inline=False,
        )
        embed.add_field(
            name="SHIPS STANDING",
            value=(
                f"**{self.session.host.display_name}:** "
                f"`{self.host_fleet.remaining_ships()}`    "
                f"**{self.session.opponent.display_name}:** "
                f"`{self.opponent_fleet.remaining_ships()}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="TURN",
            value=f"**{current.mention}** is firing",
            inline=True,
        )
        embed.add_field(name="STAKES", value=self.session.stake_line(), inline=True)
        embed.set_footer(text="SAD BOT  •  BATTLESHIP  •  S ship   x hit   o miss   # sunk")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.session.is_participant(interaction.user.id):
            await interaction.response.send_message(
                "Only the two match players can fire.",
                ephemeral=True,
            )
            return False
        if self.session.is_ai and interaction.user.id != self.session.host.id:
            return False
        if interaction.user.id != self.current_player_id:
            await interaction.response.send_message(
                "It is the other player's turn.",
                ephemeral=True,
            )
            return False
        return True

    async def finish(
        self,
        interaction: Optional[discord.Interaction],
        winner: discord.Member,
        use_response: bool,
    ) -> None:
        self.game_over = True
        disable_children(self)
        try:
            first, second, pot = await self.session.settle(winner.id)
        except sqlite3.Error:
            embed = premium_embed(
                "VAULT ERROR",
                "The match ended, but the Gem Vault could not finish settlement.",
                discord.Color.red(),
            )
            if use_response and interaction is not None:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await safe_edit(self.message, embed=embed, view=self)
            self.stop()
            return
        if self.session.stake > 0:
            description = (
                f"**{winner.mention}** sank the opposing fleet and receives "
                f"**`{pot:,} Gems`**."
            )
        else:
            description = (
                f"**{winner.mention}** sank the opposing fleet and earns match XP."
            )
        embed = premium_embed("BATTLESHIP VICTORY", description, GOLD_COLOR)
        embed.add_field(
            name=f"{self.session.host.display_name}  •  FLEET",
            value=render_battle_grid(
                self.size,
                ships=self.host_fleet.ship_cells,
                hits=self.host_fleet.hits,
                misses=self.host_fleet.misses,
                reveal_ships=True,
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{self.session.opponent.display_name}  •  FLEET",
            value=render_battle_grid(
                self.size,
                ships=self.opponent_fleet.ship_cells,
                hits=self.opponent_fleet.hits,
                misses=self.opponent_fleet.misses,
                reveal_ships=True,
            ),
            inline=False,
        )
        if first is not None:
            host_balance = account_balance(first, second, self.session.host.id)
            if host_balance is not None:
                embed.add_field(
                    name="GEM BALANCE",
                    value=f"**{self.session.host.display_name}:** `{host_balance:,} Gems`",
                    inline=False,
                )
        embed.set_footer(text="SAD BOT  •  BATTLESHIP")
        if use_response and interaction is not None:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await safe_edit(self.message, embed=embed, view=self)
        self.stop()

    async def fire(self, interaction: discord.Interaction, index: int) -> None:
        start_ai = False
        async with self.session.lock:
            if self.game_over:
                await interaction.response.send_message(
                    "This naval match has ended.",
                    ephemeral=True,
                )
                return
            fleet = self.defending_fleet(interaction.user.id)
            if fleet.already_fired(index):
                await interaction.response.send_message(
                    "That coordinate has already been fired upon.",
                    ephemeral=True,
                )
                return
            result = fleet.fire(index)
            label = grid_label(index, self.size)
            if result == "miss":
                shot_text = f"**{interaction.user.mention}** fired on **{label}**  •  miss"
            elif result == "hit":
                shot_text = f"**{interaction.user.mention}** fired on **{label}**  •  hit"
            else:
                shot_text = (
                    f"**{interaction.user.mention}** fired on **{label}**  •  ship sunk"
                )
            if fleet.defeated():
                winner = (
                    self.session.host
                    if interaction.user.id == self.session.host.id
                    else self.session.opponent
                )
                await self.finish(interaction, winner, True)
                return
            if result == "miss":
                self.current_player_id = (
                    self.session.opponent.id
                    if interaction.user.id == self.session.host.id
                    else self.session.host.id
                )
            self.sync_buttons(self.current_player_id)
            self.last_note = shot_text
            await interaction.response.edit_message(
                embed=self.build_embed(shot_text),
                view=self,
            )
            self.message = interaction.message
            start_ai = (
                self.session.is_ai
                and not self.game_over
                and self.current_player_id == self.session.opponent.id
            )
        if start_ai:
            await self.run_ai_turn()

    async def run_ai_turn(self) -> None:
        while (
            not self.game_over
            and self.current_player_id == self.session.opponent.id
        ):
            await asyncio.sleep(random.uniform(0.7, 1.25))
            async with self.session.lock:
                if self.game_over:
                    return
                fleet = self.host_fleet
                index = battleship_ai_shot(fleet)
                result = fleet.fire(index)
                label = grid_label(index, self.size)
                if result == "miss":
                    shot_text = (
                        f"**{self.session.opponent.mention}** fired on **{label}**  •  miss"
                    )
                    self.current_player_id = self.session.host.id
                elif result == "hit":
                    shot_text = (
                        f"**{self.session.opponent.mention}** fired on **{label}**  •  hit"
                    )
                else:
                    shot_text = (
                        f"**{self.session.opponent.mention}** fired on **{label}**  •  ship sunk"
                    )
                self.last_note = shot_text
                if fleet.defeated():
                    await self.finish(None, self.session.opponent, False)
                    return
                self.sync_buttons(self.current_player_id)
                await safe_edit(
                    self.message,
                    embed=self.build_embed(shot_text),
                    view=self,
                )
                if result == "miss":
                    return

    async def on_timeout(self) -> None:
        async with self.session.lock:
            if self.game_over:
                return
            self.game_over = True
            disable_children(self)
            try:
                await self.session.settle(None, cancelled=True)
            except sqlite3.Error:
                await safe_edit(
                    self.message,
                    embed=premium_embed(
                        "STAKE REFUND PENDING",
                        "The match timed out, but the Gem Vault could not refund the wager.",
                        discord.Color.red(),
                    ),
                    view=self,
                )
                return
            await safe_edit(
                self.message,
                embed=premium_embed(
                    "MATCH EXPIRED",
                    "No shot was fired in time. Any locked Gems have been returned.",
                    MUTED_COLOR,
                ),
                view=self,
            )


class BattleshipButton(discord.ui.Button):
    def __init__(self, index: int, size: int) -> None:
        super().__init__(
            label=grid_label(index, size),
            style=discord.ButtonStyle.primary,
            row=index // size,
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, BattleshipView):
            await self.view.fire(interaction, self.index)


class MultiplayerGamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, store: GemStore) -> None:
        self.bot = bot
        self.store = store

    @commands.command(name="game")
    @commands.guild_only()
    async def game(
        self,
        ctx: commands.Context,
        opponent: Optional[discord.Member] = None,
    ) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("Multiplayer games can only be started in a server.")
            return
        if opponent is None:
            await ctx.send(
                embed=premium_embed(
                    "MULTIPLAYER ARENA",
                    "Start a match with `sad game @user`.\n\n"
                    "Mention a friend for Player vs Player, or mention "
                    f"{self.bot.user.mention if self.bot.user else 'SadBot'} "
                    "for balanced AI Mode.\n"
                    "You will then choose Free Play or a Gem wager, pick a mini-game, "
                    "and set the grid size for Tic-Tac-Toe and Battleship.",
                    ARENA_COLOR,
                )
            )
            return
        if opponent.id == ctx.author.id:
            await ctx.send("You cannot challenge yourself.")
            return

        is_ai = self.bot.user is not None and opponent.id == self.bot.user.id
        if opponent.bot and not is_ai:
            await ctx.send("Challenge a server member, or mention this bot for AI Mode.")
            return

        session = MatchSession(
            host=ctx.author,
            opponent=opponent,
            is_ai=is_ai,
            store=self.store,
        )
        view = BetModeView(session)
        if is_ai:
            description = (
                f"**{ctx.author.mention}** opened AI Mode against "
                f"**{opponent.mention}**.\n\n"
                "SadBot plays a balanced casual style: strong enough to win, "
                "human enough to miss. Choose Free Play or set a Gem wager."
            )
        else:
            description = (
                f"**{ctx.author.mention}** is challenging **{opponent.mention}**.\n\n"
                "Choose **Free Play** for a casual match, or **Gem Wager** to lock "
                "the same Gem amount from both players."
            )
        embed = premium_embed("MATCH SETUP", description, ARENA_COLOR)
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    store = getattr(bot, "gem_store", None)
    if not isinstance(store, GemStore):
        raise RuntimeError(
            "GemStore must be initialized before loading multiplayer_games_cog."
        )
    await bot.add_cog(MultiplayerGamesCog(bot, store))
