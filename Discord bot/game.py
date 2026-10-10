import asyncio
import random
import sqlite3
from typing import List, Optional, Set

import discord
from discord.ext import commands

from gem_store import GemAccount, GemStore


ROUND_STAKE = 250
MINE_COUNT = 2
XP_ROUND_COMPLETE = 20
XP_PER_SAFE_PICK = 10


class MinesView(discord.ui.View):
    def __init__(
        self,
        author: discord.User,
        store: GemStore,
        balance_after_stake: int,
        bet: int = ROUND_STAKE,
        mine_count: int = MINE_COUNT,
    ) -> None:
        super().__init__(timeout=120)
        self.author = author
        self.store = store
        self.bet = bet
        self.mine_count = mine_count
        self.multiplier = 1.0
        self.game_over = False
        self.balance_after_stake = balance_after_stake
        self.mine_indices: Set[int] = set(random.sample(range(9), mine_count))
        self.revealed_indices: Set[int] = set()
        self.grid_buttons: List[MinesGridButton] = []
        self.message: Optional[discord.Message] = None
        self.lock = asyncio.Lock()

        for index in range(9):
            button = MinesGridButton(index)
            self.grid_buttons.append(button)
            self.add_item(button)
        self.cash_out_button = MinesCashOutButton()
        self.cash_out_button.disabled = True
        self.add_item(self.cash_out_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ This Mines round belongs to another player.", ephemeral=True
            )
            return False
        return True

    @property
    def possible_payout(self) -> int:
        return int(self.bet * self.multiplier)

    def xp_reward(self, payout: int) -> int:
        return (
            XP_ROUND_COMPLETE
            + XP_PER_SAFE_PICK * len(self.revealed_indices)
            + max(0, payout - self.bet) // 10
        )

    def build_embed(
        self,
        title: str,
        description: str,
        color: discord.Color,
        balance: Optional[int] = None,
    ) -> discord.Embed:
        shown_balance = (
            self.balance_after_stake if balance is None else balance
        )
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_author(name=f"{self.author.display_name} • MINES")
        embed.add_field(
            name="💎  ROUND STAKE",
            value=f"`{self.bet:,} Gems`",
            inline=True,
        )
        embed.add_field(
            name="🟢  SAFE PICKS",
            value=f"`{len(self.revealed_indices)}`",
            inline=True,
        )
        embed.add_field(
            name="📈  MULTIPLIER",
            value=f"`{self.multiplier:.2f}x`",
            inline=True,
        )
        embed.add_field(
            name="🏆  POTENTIAL PAYOUT",
            value=f"`{self.possible_payout:,} Gems`",
            inline=True,
        )
        embed.add_field(
            name="👑  WALLET BALANCE",
            value=f"`{shown_balance:,} Gems`",
            inline=True,
        )
        embed.set_footer(
            text="💎 REVEAL A SAFE TILE  •  💰 CASH OUT TO SECURE YOUR PAYOUT"
        )
        return embed

    def disable_controls(self) -> None:
        for child in self.children:
            child.disabled = True

    async def _settle(self, payout: int) -> GemAccount:
        return await self.store.settle_game(
            self.author.id,
            payout=payout,
            xp_earned=self.xp_reward(payout),
        )

    async def on_timeout(self) -> None:
        async with self.lock:
            if self.game_over:
                return
            try:
                account = await self._settle(0)
            except sqlite3.Error:
                if self.message:
                    error_embed = discord.Embed(
                        title="⚠️  ROUND SETTLEMENT ERROR",
                        description=(
                            "The round timed out, but its Gem settlement could not "
                            "be saved. Please contact a server administrator."
                        ),
                        color=discord.Color.red(),
                    )
                    error_embed.set_footer(text="✦ SAD BOT  •  MINES SUPPORT")
                    await self.message.edit(
                        content=None,
                        embed=error_embed,
                        view=None,
                    )
                return

            self.game_over = True
            self.disable_controls()
            if self.message:
                embed = self.build_embed(
                    "⏰ Round Expired",
                    f"Your **{self.bet:,}-Gem stake** was lost when the round expired.\n"
                    f"✨ XP earned: `{self.xp_reward(0)}`",
                    discord.Color.dark_grey(),
                    account.balance,
                )
                await self.message.edit(embed=embed, view=self)

    async def reveal(self, interaction: discord.Interaction, index: int) -> None:
        async with self.lock:
            if self.game_over:
                await interaction.response.send_message(
                    "⚠️ This round has already ended.", ephemeral=True
                )
                return

            if index in self.revealed_indices:
                await interaction.response.send_message(
                    "⚠️ You already revealed this tile.", ephemeral=True
                )
                return

            if index in self.mine_indices:
                try:
                    account = await self._settle(0)
                except sqlite3.Error:
                    await interaction.response.send_message(
                        "⚠️ The result could not be saved. Please try again.",
                        ephemeral=True,
                    )
                    return

                self.game_over = True
                self.disable_controls()
                for grid_button in self.grid_buttons:
                    if grid_button.index in self.mine_indices:
                        grid_button.emoji = "💣"
                        grid_button.style = discord.ButtonStyle.danger
                    else:
                        grid_button.emoji = "💎"
                        grid_button.style = discord.ButtonStyle.success

                embed = self.build_embed(
                    "💥 Mine Hit!",
                    f"**{self.author.mention}** hit a mine and lost the "
                    f"**{self.bet:,}-Gem stake**.\n✨ XP earned: `{self.xp_reward(0)}`",
                    discord.Color.red(),
                    account.balance,
                )
                embed.set_field_at(
                    3, name="🏆 Final Payout", value="`0 Gems`", inline=True
                )
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            self.revealed_indices.add(index)
            button = self.grid_buttons[index]
            button.emoji = "💎"
            button.style = discord.ButtonStyle.success
            button.disabled = True
            self.multiplier += 0.41
            self.cash_out_button.disabled = False

            if len(self.revealed_indices) == 9 - self.mine_count:
                await self._cash_out(interaction, board_cleared=True)
                return

            embed = self.build_embed(
                "💎 Safe Tile!",
                f"✨ **{self.author.mention}** found a Gem!\n"
                "Continue carefully, or secure your payout with **Cash Out**.",
                discord.Color.from_rgb(125, 85, 235),
            )
            await interaction.response.edit_message(embed=embed, view=self)

    async def cash_out(self, interaction: discord.Interaction) -> None:
        async with self.lock:
            if self.game_over:
                await interaction.response.send_message(
                    "⚠️ This round has already ended.", ephemeral=True
                )
                return
            if not self.revealed_indices:
                await interaction.response.send_message(
                    "💎 Reveal at least one safe tile before cashing out.",
                    ephemeral=True,
                )
                return
            await self._cash_out(interaction)

    async def _cash_out(
        self, interaction: discord.Interaction, board_cleared: bool = False
    ) -> None:
        payout = self.possible_payout
        try:
            account = await self._settle(payout)
        except sqlite3.Error:
            await interaction.response.send_message(
                "⚠️ The payout could not be saved. Please try again.",
                ephemeral=True,
            )
            return

        self.game_over = True
        self.disable_controls()
        if board_cleared:
            title = "🎉 Board Cleared!"
            description = f"✨ **{self.author.mention}** found every safe tile!"
        else:
            title = "💰 Gems Secured!"
            description = f"✅ **{self.author.mention}** cashed out safely."
        embed = self.build_embed(title, description, discord.Color.gold(), account.balance)
        embed.add_field(
            name="💰  SECURED PAYOUT",
            value=f"`{payout:,} Gems`  •  `{self.multiplier:.2f}x`",
            inline=False,
        )
        embed.add_field(
            name="✨  XP EARNED",
            value=f"`{self.xp_reward(payout)}`",
            inline=True,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class MinesGridButton(discord.ui.Button):
    def __init__(self, index: int) -> None:
        super().__init__(style=discord.ButtonStyle.secondary, emoji="❔", row=index // 3)
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, MinesView):
            await self.view.reveal(interaction, self.index)


class MinesCashOutButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Cash Out",
            style=discord.ButtonStyle.success,
            emoji="💰",
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, MinesView):
            await self.view.cash_out(interaction)


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot, store: GemStore) -> None:
        self.bot = bot
        self.store = store

    @commands.command(name="um")
    async def um(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("🎮 Mines can only be played in a server.")
            return

        try:
            placed, remaining_balance = await self.store.place_bet(
                ctx.author.id, ROUND_STAKE
            )
        except sqlite3.Error:
            await ctx.send("⚠️ The Gem wallet is temporarily unavailable.")
            return

        if not placed:
            await ctx.send(
                f"💎 You need **{ROUND_STAKE:,} Gems** to play. "
                f"Your balance is **`{remaining_balance:,}`**."
            )
            return

        view = MinesView(ctx.author, self.store, remaining_balance)
        embed = view.build_embed(
            "💣  MINES  •  GEM VAULT",
            (
                f"{ctx.author.mention} entered the Mines.\n"
                f"**💣 Mines:** `{MINE_COUNT}`  •  "
                f"**💎 Stake:** `{ROUND_STAKE:,} Gems`\n\n"
                "Reveal a tile to begin. Find 💎 safe tiles to raise your "
                "multiplier, then cash out to secure your payout."
            ),
            discord.Color.from_rgb(92, 61, 190),
        )
        try:
            view.message = await ctx.send(embed=embed, view=view)
        except discord.HTTPException:
            await self.store.refund(ctx.author.id, ROUND_STAKE)
            raise


async def setup(bot: commands.Bot) -> None:
    store = getattr(bot, "gem_store", None)
    if not isinstance(store, GemStore):
        raise RuntimeError("GemStore must be initialized before loading the game extension.")
    await bot.add_cog(GameCog(bot, store))
