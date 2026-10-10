import asyncio
import random
import sqlite3
import uuid
from typing import Dict, List, Optional, Sequence, Tuple

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
TIC_TAC_TOE_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def premium_embed(
    title: str, description: str, color: discord.Color
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="✦ SAD BOT  •  MULTIPLAYER ARENA")
    return embed


def account_balance(
    player_one: Optional[GemAccount], player_two: Optional[GemAccount], user_id: int
) -> Optional[int]:
    for account in (player_one, player_two):
        if account is not None and account.user_id == user_id:
            return account.balance
    return None


class ChallengeView(discord.ui.View):
    def __init__(
        self,
        challenger: discord.Member,
        opponent: discord.Member,
        stake: int,
        store: GemStore,
    ) -> None:
        super().__init__(timeout=120)
        self.challenger = challenger
        self.opponent = opponent
        self.stake = stake
        self.store = store
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.opponent:
            await interaction.response.send_message(
                "This challenge is for the invited player only.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(
                embed=premium_embed(
                    "⏰  CHALLENGE EXPIRED",
                    "The invitation expired without starting a match.",
                    discord.Color.dark_grey(),
                ),
                view=self,
            )

    @discord.ui.button(
        label="Accept Challenge",
        style=discord.ButtonStyle.success,
        emoji="⚔️",
    )
    async def accept(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view = GameModeView(
            self.challenger,
            self.opponent,
            self.stake,
            self.store,
        )
        view.message = interaction.message
        for child in self.children:
            child.disabled = True
        embed = premium_embed(
            "🎮  SELECT YOUR GAME",
            f"**{self.challenger.mention}** and **{self.opponent.mention}** are ready.\n\n"
            f"Choose **Tic-Tac-Toe** or **Khla Klok** below.\n"
            f"Khla Klok match stake: **`{self.stake:,} Gems` per player**.",
            discord.Color.from_rgb(94, 72, 190),
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
        for child in self.children:
            child.disabled = True
        embed = premium_embed(
            "CHALLENGE DECLINED",
            f"{self.opponent.mention} declined the game invitation.",
            discord.Color.dark_grey(),
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class GameModeView(discord.ui.View):
    def __init__(
        self,
        challenger: discord.Member,
        opponent: discord.Member,
        stake: int,
        store: GemStore,
    ) -> None:
        super().__init__(timeout=120)
        self.challenger = challenger
        self.opponent = opponent
        self.stake = stake
        self.store = store
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.challenger:
            await interaction.response.send_message(
                "Only the challenger can select the game mode.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(
                embed=premium_embed(
                    "⏰  GAME SELECTION EXPIRED",
                    "The game mode was not selected in time.",
                    discord.Color.dark_grey(),
                ),
                view=self,
            )

    @discord.ui.button(
        label="Tic-Tac-Toe",
        style=discord.ButtonStyle.primary,
        emoji="❎",
    )
    async def tic_tac_toe(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view = TicTacToeView(self.challenger, self.opponent, self.store)
        view.message = interaction.message
        embed = view.board_embed("TIC-TAC-TOE", "Choose a square to make your move.")
        await interaction.response.edit_message(embed=embed, view=view)
        self.stop()

    @discord.ui.button(
        label="Khla Klok",
        style=discord.ButtonStyle.success,
        emoji="🐯",
    )
    async def khla_klok(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.stake <= 0 or self.stake > MAX_SQLITE_INTEGER // 2:
            await interaction.response.send_message(
                "The selected Gem stake is outside the supported range.",
                ephemeral=True,
            )
            return

        match_id = uuid.uuid4().hex
        try:
            reserved, challenger_balance, opponent_balance = (
                await self.store.reserve_multiplayer_stake(
                    match_id,
                    self.challenger.id,
                    self.opponent.id,
                    self.stake,
                )
            )
        except sqlite3.Error:
            await interaction.response.send_message(
                "The Gem Vault is temporarily unavailable. No stake was taken.",
                ephemeral=True,
            )
            return

        if not reserved:
            embed = premium_embed(
                "💎  INSUFFICIENT GEMS",
                f"Both players need **`{self.stake:,} Gems`** to enter Khla Klok.\n\n"
                f"**{self.challenger.display_name}:** `{challenger_balance:,} Gems`\n"
                f"**{self.opponent.display_name}:** `{opponent_balance:,} Gems`",
                discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return

        view = KhlaKlokView(
            self.challenger,
            self.opponent,
            self.stake,
            match_id,
            self.store,
        )
        view.message = interaction.message
        embed = view.build_embed(
            "🐯  K H L A  K L O K",
            "Each player selects one animal. Three dice will decide the winner.\n"
            f"**Stake:** `{self.stake:,} Gems` from each player",
            None,
            None,
        )
        await interaction.response.edit_message(embed=embed, view=view)
        self.stop()


class TicTacToeView(discord.ui.View):
    def __init__(
        self,
        player_x: discord.Member,
        player_o: discord.Member,
        store: GemStore,
    ) -> None:
        super().__init__(timeout=180)
        self.player_x = player_x
        self.player_o = player_o
        self.store = store
        self.current_player_id = player_x.id
        self.board: List[Optional[str]] = [None] * 9
        self.game_over = False
        self.message: Optional[discord.Message] = None
        self.lock = asyncio.Lock()
        for index in range(9):
            self.add_item(TicTacToeButton(index))

    def player_for(self, mark: str) -> discord.Member:
        return self.player_x if mark == "X" else self.player_o

    def board_embed(self, title: str, description: str) -> discord.Embed:
        embed = premium_embed(title, description, discord.Color.from_rgb(77, 118, 220))
        embed.add_field(
            name="📊  BOARD",
            value="\n".join(
                "  ·  ".join(
                    self.board[row * 3 + col]
                    or str(row * 3 + col + 1)
                    for col in range(3)
                )
                for row in range(3)
            ),
            inline=False,
        )
        next_mark = "X" if self.current_player_id == self.player_x.id else "O"
        embed.add_field(
            name="⚡  TURN",
            value=f"**{self.player_for(next_mark).mention}**  •  `{next_mark}`",
            inline=False,
        )
        embed.set_footer(text="X starts • Make a line of three to win")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.player_x.id, self.player_o.id):
            await interaction.response.send_message(
                "Only the two invited players can make a move.",
                ephemeral=True,
            )
            return False
        if interaction.user.id != self.current_player_id:
            await interaction.response.send_message(
                "It is the other player's turn.",
                ephemeral=True,
            )
            return False
        return True

    async def play(self, interaction: discord.Interaction, index: int) -> None:
        async with self.lock:
            if self.game_over or self.board[index] is not None:
                await interaction.response.send_message(
                    "That square is no longer available.",
                    ephemeral=True,
                )
                return

            mark = "X" if self.current_player_id == self.player_x.id else "O"
            self.board[index] = mark
            self.children[index].label = mark
            self.children[index].style = (
                discord.ButtonStyle.primary
                if mark == "X"
                else discord.ButtonStyle.success
            )
            winner: Optional[str] = None
            for line in TIC_TAC_TOE_LINES:
                first_mark = self.board[line[0]]
                if (
                    first_mark is not None
                    and first_mark == self.board[line[1]] == self.board[line[2]]
                ):
                    winner = first_mark
                    break
            is_draw = winner is None and all(cell is not None for cell in self.board)

            if winner or is_draw:
                self.game_over = True
                for child in self.children:
                    child.disabled = True

                if winner:
                    champion = self.player_for(winner)
                    try:
                        await self.store.award_xp(champion.id, 20)
                        result = f"🏆 **{champion.mention}** wins and earns `20 XP`."
                    except sqlite3.Error:
                        result = f"🏆 **{champion.mention}** wins the match."
                    title = "🏆  VICTORY"
                else:
                    try:
                        await asyncio.gather(
                            self.store.award_xp(self.player_x.id, 10),
                            self.store.award_xp(self.player_o.id, 10),
                        )
                        result = "✨ The match is a draw. Both players earn `10 XP`."
                    except sqlite3.Error:
                        result = "✨ The match is a draw."
                    title = "🤝  MATCH DRAW"

                embed = premium_embed(
                    title,
                    result,
                    discord.Color.gold() if winner else discord.Color.blurple(),
                )
                embed.add_field(
                    name="📊  FINAL BOARD",
                    value="\n".join(
                        "  ·  ".join(
                            self.board[row * 3 + col] or "—"
                            for col in range(3)
                        )
                        for row in range(3)
                    ),
                    inline=False,
                )
                embed.set_footer(text="✦ SAD BOT  •  TIC-TAC-TOE")
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            self.current_player_id = (
                self.player_o.id if mark == "X" else self.player_x.id
            )
            await interaction.response.edit_message(
                embed=self.board_embed(
                    "❎  TIC-TAC-TOE",
                    f"**{self.player_for(mark).mention}** placed **{mark}**.",
                ),
                view=self,
            )

    async def on_timeout(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(
                embed=premium_embed(
                    "⏰  MATCH EXPIRED",
                    "The Tic-Tac-Toe match ended because no move was made in time.",
                    discord.Color.dark_grey(),
                ),
                view=self,
            )


class TicTacToeButton(discord.ui.Button):
    def __init__(self, index: int) -> None:
        super().__init__(
            label=str(index + 1),
            style=discord.ButtonStyle.secondary,
            row=index // 3,
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, TicTacToeView):
            await self.view.play(interaction, self.index)


class KhlaKlokView(discord.ui.View):
    def __init__(
        self,
        player_one: discord.Member,
        player_two: discord.Member,
        stake: int,
        match_id: str,
        store: GemStore,
    ) -> None:
        super().__init__(timeout=180)
        self.players = (player_one, player_two)
        self.stake = stake
        self.match_id = match_id
        self.store = store
        self.selections: Dict[int, int] = {}
        self.game_over = False
        self.message: Optional[discord.Message] = None
        self.lock = asyncio.Lock()
        for index, (emoji, english, khmer) in enumerate(ANIMALS):
            self.add_item(KhlaChoiceButton(index, emoji, english, khmer))

    def build_embed(
        self,
        title: str,
        description: str,
        dice: Optional[Sequence[int]],
        balances: Optional[Tuple[Optional[int], Optional[int]]],
    ) -> discord.Embed:
        embed = premium_embed(title, description, discord.Color.from_rgb(40, 130, 105))
        for index, player in enumerate(self.players):
            selection = self.selections.get(player.id)
            selection_text = (
                "Choosing..."
                if selection is None
                else f"{ANIMALS[selection][0]} {ANIMALS[selection][1]} {ANIMALS[selection][2]}"
            )
            balance_text = (
                f"\nBalance: `{balances[index]:,} Gems`"
                if balances is not None and balances[index] is not None
                else ""
            )
            embed.add_field(
                name=f"🎯  {player.display_name}",
                value=f"Selection: **{selection_text}**{balance_text}",
                inline=True,
            )
        if dice is not None:
            dice_text = "  •  ".join(
                f"{ANIMALS[result][0]} {ANIMALS[result][1]} {ANIMALS[result][2]}"
                for result in dice
            )
            embed.add_field(name="🎲  THREE DICE", value=dice_text, inline=False)
        embed.add_field(
            name="💎  MATCH STAKE",
            value=f"`{self.stake:,} Gems` per player",
            inline=False,
        )
        embed.set_footer(text="Choose one animal • Three dice decide the result")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (player.id for player in self.players):
            await interaction.response.send_message(
                "Only the two invited players can place a selection.",
                ephemeral=True,
            )
            return False
        return True

    async def choose(self, interaction: discord.Interaction, selection: int) -> None:
        async with self.lock:
            if self.game_over:
                await interaction.response.send_message(
                    "This Khla Klok round has ended.",
                    ephemeral=True,
                )
                return

            self.selections[interaction.user.id] = selection
            if len(self.selections) < 2:
                embed = self.build_embed(
                    "🐯  K H L A  K L O K",
                    f"**{interaction.user.mention}** selected "
                    f"**{ANIMALS[selection][1]} {ANIMALS[selection][2]}**.\n"
                    "Waiting for the other player to select an animal.",
                    None,
                    None,
                )
                await interaction.response.edit_message(embed=embed, view=self)
                return

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
                settled, first_account, second_account, pot = (
                    await self.store.settle_multiplayer_match(
                        self.match_id,
                        winner_id,
                    )
                )
            except sqlite3.Error:
                del self.selections[interaction.user.id]
                await interaction.response.send_message(
                    "The Gem Vault could not settle this round. Please try again.",
                    ephemeral=True,
                )
                return

            if not settled:
                self.game_over = True
                self.disable_all()
                await interaction.response.edit_message(
                    embed=premium_embed(
                        "⚠️  MATCH ALREADY SETTLED",
                        "This match has already been finalized or its stake is unavailable.",
                        discord.Color.orange(),
                    ),
                    view=self,
                )
                self.stop()
                return

            self.game_over = True
            self.disable_all()
            balances = (
                account_balance(first_account, second_account, self.players[0].id),
                account_balance(first_account, second_account, self.players[1].id),
            )
            if winner_id is None:
                result_title = "🤝  KHLA KLOK DRAW"
                result_description = (
                    "The players matched counts. Both Gem stakes have been returned."
                )
            else:
                winner = next(player for player in self.players if player.id == winner_id)
                result_title = "🏆  KHLA KLOK VICTORY"
                result_description = (
                    f"**{winner.mention}** wins the match and receives "
                    f"**`{pot:,} Gems`**."
                )

            embed = self.build_embed(
                result_title,
                result_description,
                dice,
                balances,
            )
            embed.add_field(
                name="📊  ANIMAL COUNTS",
                value="\n".join(
                    f"{player.mention}: **{counts[player.id]}** "
                    f"{ANIMALS[self.selections[player.id]][0]} "
                    f"{ANIMALS[self.selections[player.id]][1]} "
                    f"{ANIMALS[self.selections[player.id]][2]}"
                    for player in self.players
                ),
                inline=False,
            )
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()

    def disable_all(self) -> None:
        for child in self.children:
            child.disabled = True

    async def on_timeout(self) -> None:
        async with self.lock:
            if self.game_over:
                return
            try:
                settled, first_account, second_account, _ = (
                    await self.store.settle_multiplayer_match(self.match_id, None)
                )
            except sqlite3.Error:
                if self.message:
                    await self.message.edit(
                        embed=premium_embed(
                            "⚠️  STAKE REFUND PENDING",
                            "The match timed out, but the Gem Vault could not process "
                            "the stake refund. Please contact a server administrator.",
                            discord.Color.red(),
                        ),
                        view=None,
                    )
                return

            self.game_over = True
            self.disable_all()
            if self.message and settled:
                balances = (
                    account_balance(first_account, second_account, self.players[0].id),
                    account_balance(first_account, second_account, self.players[1].id),
                )
                await self.message.edit(
                    embed=self.build_embed(
                        "⏰  KHLA KLOK EXPIRED",
                        "The round timed out. Both Gem stakes have been returned.",
                        None,
                        balances,
                    ),
                    view=self,
                )


class KhlaChoiceButton(discord.ui.Button):
    def __init__(self, index: int, emoji: str, english: str, khmer: str) -> None:
        super().__init__(
            label=f"{english} {khmer}",
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            row=index // 3,
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, KhlaKlokView):
            if await self.view.interaction_check(interaction):
                await self.view.choose(interaction, self.index)


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
        stake_text: Optional[str] = None,
    ) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("Multiplayer games can only be started in a server.")
            return
        if opponent is None:
            await ctx.send(
                embed=premium_embed(
                    "🎮  MULTIPLAYER CHALLENGE",
                    "Challenge a server member with `sad game @user [stake]`.\n"
                    "The optional stake applies to Khla Klok; both players stake the same amount.",
                    discord.Color.blurple(),
                )
            )
            return
        if opponent.bot:
            await ctx.send("🤖 You can only challenge another player.")
            return
        if opponent.id == ctx.author.id:
            await ctx.send("⚠️ You cannot challenge yourself.")
            return

        stake = 100
        if stake_text is not None:
            try:
                stake = int(stake_text)
            except ValueError:
                await ctx.send("Enter a positive whole-number Gem stake.")
                return
        if stake <= 0 or stake > MAX_SQLITE_INTEGER // 2:
            await ctx.send("Choose a positive stake within the supported Gem limit.")
            return

        view = ChallengeView(ctx.author, opponent, stake, self.store)
        embed = premium_embed(
            "⚔️  GAME CHALLENGE",
            f"**{ctx.author.mention}** challenged **{opponent.mention}**.\n\n"
            "Accept the invitation to choose Tic-Tac-Toe or Khla Klok.\n"
            f"Khla Klok stake: **`{stake:,} Gems`** per player. "
            "Tic-Tac-Toe is free to play.",
            discord.Color.from_rgb(93, 72, 190),
        )
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    store = getattr(bot, "gem_store", None)
    if not isinstance(store, GemStore):
        raise RuntimeError(
            "GemStore must be initialized before loading multiplayer_games_cog."
        )
    await bot.add_cog(MultiplayerGamesCog(bot, store))
