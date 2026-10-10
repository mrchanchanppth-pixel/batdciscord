import sqlite3
from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

from gem_store import (
    DAILY_CLAIM_GEMS,
    GemStore,
    MAX_LEVEL,
    XP_PER_LEVEL,
)


def claim_embed(
    title: str, description: str, color: discord.Color
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="✦ SAD BOT  •  DAILY GEM VAULT")
    return embed


class DailyClaimView(discord.ui.View):
    def __init__(self, author: discord.User, store: GemStore) -> None:
        super().__init__(timeout=90)
        self.author = author
        self.store = store
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message(
                "This daily claim belongs to another player.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(
        label="Claim Daily Gems",
        style=discord.ButtonStyle.success,
        emoji="💎",
    )
    async def claim(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        try:
            status, account, seconds_remaining = await self.store.claim_daily(
                self.author.id
            )
        except sqlite3.Error:
            embed = claim_embed(
                "⚠️  CLAIM UNAVAILABLE",
                "Your claim could not be processed. Please try again shortly.",
                discord.Color.red(),
            )
            await interaction.edit_original_response(embed=embed, view=self)
            return

        if status == "cooldown":
            next_claim = int(
                (discord.utils.utcnow() + timedelta(seconds=seconds_remaining)).timestamp()
            )
            embed = claim_embed(
                "⏳  DAILY CLAIM NOT READY",
                f"You have already claimed today's reward.\n\n"
                f"Your next **{DAILY_CLAIM_GEMS}-Gem** claim is available <t:{next_claim}:R>.",
                discord.Color.blurple(),
            )
        elif status == "capacity":
            embed = claim_embed(
                "💎  GEM VAULT FULL",
                "Your Gem balance is at its storage limit, so this reward cannot be credited.",
                discord.Color.orange(),
            )
        else:
            embed = claim_embed(
                "✨  DAILY GEMS CLAIMED",
                f"**{self.author.mention}**, your reward is ready.\n\n"
                f"**Reward:** `{DAILY_CLAIM_GEMS:,} Gems`\n"
                f"**New Balance:** `{account.balance:,} Gems`\n"
                f"**Next Claim:** <t:{int(discord.utils.utcnow().timestamp()) + 86400}:R>",
                discord.Color.gold(),
            )

        for child in self.children:
            child.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="✖️",
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        for child in self.children:
            child.disabled = True
        embed = claim_embed(
            "Claim Cancelled",
            "No Gems were added to your wallet.",
            discord.Color.dark_grey(),
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot, store: GemStore) -> None:
        self.bot = bot
        self.store = store

    @commands.command(name="bal", aliases=("balance",))
    async def balance(self, ctx: commands.Context) -> None:
        try:
            account = await self.store.get_account(ctx.author.id)
        except sqlite3.Error:
            await ctx.send("⚠️ Your Gem Vault is temporarily unavailable.")
            return
        embed = discord.Embed(
            title="💎  GEM VAULT",
            description=(
                f"Welcome back, {ctx.author.mention}.\n"
                "Your current Gem balance and progression at a glance."
            ),
            color=discord.Color.from_rgb(100, 70, 220),
        )
        embed.add_field(
            name="💎  AVAILABLE GEMS",
            value=f"`{account.balance:,}`",
            inline=True,
        )
        embed.add_field(
            name="👑  LEVEL",
            value=f"`{account.level} / {MAX_LEVEL}`",
            inline=True,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="✦ SAD BOT  •  GEM VAULT")
        await ctx.send(embed=embed)

    @commands.command(name="pay")
    @commands.guild_only()
    async def pay(
        self,
        ctx: commands.Context,
        recipient: Optional[discord.Member] = None,
        amount: Optional[str] = None,
    ) -> None:
        if recipient is None or amount is None:
            await ctx.send("📖 Usage: `sad pay @user <amount>`")
            return
        if recipient.bot:
            await ctx.send("🤖 Gems can only be transferred to another person.")
            return
        if recipient.id == ctx.author.id:
            await ctx.send("⚠️ You cannot transfer Gems to yourself.")
            return
        try:
            gem_amount = int(amount)
        except ValueError:
            await ctx.send("⚠️ Enter a positive whole-number Gem amount.")
            return
        if gem_amount <= 0:
            await ctx.send("⚠️ Enter a positive whole-number Gem amount.")
            return
        if gem_amount > 9_223_372_036_854_775_807:
            await ctx.send("⚠️ That Gem amount is too large to transfer.")
            return

        try:
            transferred, remaining = await self.store.transfer(
                ctx.author.id, recipient.id, gem_amount
            )
        except sqlite3.Error:
            await ctx.send(
                "⚠️ The Gem transfer could not be processed. Please try again."
            )
            return
        if not transferred:
            await ctx.send(
                f"💎 You do not have enough Gems. Your balance is **`{remaining:,}`**."
            )
            return

        embed = discord.Embed(
            title="✨  GEM TRANSFER COMPLETE",
            description=(
                "Transfer confirmed.\n"
                f"**{ctx.author.mention}** sent **`{gem_amount:,} Gems`** "
                f"to **{recipient.mention}**."
            ),
            color=discord.Color.green(),
        )
        embed.add_field(
            name="📤  YOUR REMAINING BALANCE",
            value=f"`{remaining:,} Gems`",
            inline=True,
        )
        embed.set_thumbnail(url=recipient.display_avatar.url)
        embed.set_footer(text="🔒 SECURE • ATOMIC TRANSFER")
        await ctx.send(embed=embed)

    @commands.command(name="up", aliases=("level",))
    async def level(self, ctx: commands.Context) -> None:
        try:
            account = await self.store.get_account(ctx.author.id)
        except sqlite3.Error:
            await ctx.send("⚠️ Your level data is temporarily unavailable.")
            return
        if account.level >= MAX_LEVEL:
            progress = "🏆 **Maximum level reached!**"
        else:
            remaining = XP_PER_LEVEL - account.xp_into_level
            progress = f"✨ **{remaining} XP** to Level `{account.level + 1}`"

        embed = discord.Embed(
            title="👑  PLAYER PROGRESSION",
            description=(
                f"{ctx.author.mention}\n"
                "Your current level and next milestone."
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="🏆  CURRENT LEVEL",
            value=f"`{account.level} / {MAX_LEVEL}`",
            inline=True,
        )
        embed.add_field(
            name="✨  TOTAL XP",
            value=f"`{account.xp:,}`",
            inline=True,
        )
        embed.add_field(
            name="📈  NEXT MILESTONE",
            value=progress,
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="💎 PLAY MINES  •  EARN XP  •  REACH LEVEL 100")
        await ctx.send(embed=embed)

    @commands.command(name="d", aliases=("daily", "claim"))
    async def daily(self, ctx: commands.Context) -> None:
        view = DailyClaimView(ctx.author, self.store)
        embed = claim_embed(
            "💎  DAILY GEM CLAIM",
            f"Claim **`{DAILY_CLAIM_GEMS:,} Gems`** once every 24 hours.\n\n"
            "Press **Claim Daily Gems** to add the reward to your wallet, "
            "or **Cancel** to leave your balance unchanged.",
            discord.Color.from_rgb(102, 72, 210),
        )
        embed.add_field(
            name="✨  DAILY REWARD",
            value=f"`{DAILY_CLAIM_GEMS:,} Gems`",
            inline=True,
        )
        embed.add_field(
            name="⏱️  CLAIM INTERVAL",
            value="Once every 24 hours",
            inline=True,
        )
        embed.set_author(name=f"{ctx.author.display_name} • DAILY REWARD")
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    store = getattr(bot, "gem_store", None)
    if not isinstance(store, GemStore):
        raise RuntimeError("GemStore must be initialized before loading economy_cog.")
    await bot.add_cog(EconomyCog(bot, store))
