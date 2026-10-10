import asyncio
import random
import sqlite3
from typing import Dict, Optional, Tuple

import discord
from discord.ext import commands

from gem_store import GemStore, MAX_SQLITE_INTEGER


DEFAULT_BET = 100
JACKPOT_SYMBOLS = ("💎", "🔷", "💎")
JACKPOT_MINIMUM_PAYOUT = 400
JACKPOT_MULTIPLIER = 20
TRIPLE_MATCH_MULTIPLIER = 5
PAIR_MATCH_MULTIPLIER = 2
SPIN_XP = 10

REEL_SYMBOLS = ("🦊", "⭐", "🍒", "🍋", "👑", "🔥", "💎", "🔷")
SPIN_FRAMES = (
    ("🔄", "🔄", "🔄"),
    ("🎡", "🔄", "✨"),
)
COLORS: Dict[str, discord.Color] = {
    "win": discord.Color.from_rgb(104, 72, 214),
    "jackpot": discord.Color.gold(),
    "loss": discord.Color.from_rgb(75, 80, 96),
    "error": discord.Color.red(),
}


def calculate_payout(reels: Tuple[str, str, str], bet: int) -> Tuple[int, str, bool]:
    if reels == JACKPOT_SYMBOLS:
        return max(JACKPOT_MINIMUM_PAYOUT, bet * JACKPOT_MULTIPLIER), "jackpot", True
    if reels[0] == reels[1] == reels[2]:
        return bet * TRIPLE_MATCH_MULTIPLIER, "triple", True
    if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        return bet * PAIR_MATCH_MULTIPLIER, "pair", True
    return 0, "loss", False


def spin_reels() -> Tuple[str, str, str]:
    if random.random() < 0.002:
        return JACKPOT_SYMBOLS

    reels = tuple(random.choice(REEL_SYMBOLS) for _ in range(3))
    while reels == JACKPOT_SYMBOLS:
        reels = tuple(random.choice(REEL_SYMBOLS) for _ in range(3))
    return reels


def build_slots_embed(
    title: str,
    description: str,
    color: discord.Color,
    *,
    bet: Optional[int] = None,
    reels: Optional[Tuple[str, str, str]] = None,
    payout: Optional[int] = None,
    balance: Optional[int] = None,
    level: Optional[int] = None,
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    if reels is not None:
        embed.add_field(
            name="🎡  REELS",
            value=f"`[ {reels[0]}  •  {reels[1]}  •  {reels[2]} ]`",
            inline=False,
        )
    if bet is not None:
        embed.add_field(name="💎  WAGER", value=f"`{bet:,} Gems`", inline=True)
    if payout is not None:
        embed.add_field(name="🏆  PAYOUT", value=f"`{payout:,} Gems`", inline=True)
    if balance is not None:
        embed.add_field(
            name="👑  NEW BALANCE",
            value=f"`{balance:,} Gems`",
            inline=True,
        )
    if level is not None:
        embed.add_field(name="✨  LEVEL", value=f"`{level}/100`", inline=True)
    embed.set_footer(text="✦ SAD BOT  •  PREMIUM SLOTS")
    return embed


class SlotsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, store: GemStore) -> None:
        self.bot = bot
        self.store = store

    @commands.command(name="p", aliases=("spin", "slot"))
    async def slots(
        self, ctx: commands.Context, bet_text: Optional[str] = None
    ) -> None:
        if bet_text is None or bet_text.casefold() == "all":
            bet = DEFAULT_BET
        else:
            try:
                bet = int(bet_text)
            except ValueError:
                await ctx.send(
                    embed=build_slots_embed(
                        "⚠️  INVALID WAGER",
                        "Use `sad p all` for the standard **100 Gem** wager, "
                        "or enter a positive whole-number amount.",
                        COLORS["error"],
                    )
                )
                return

        if bet <= 0:
            await ctx.send(
                embed=build_slots_embed(
                    "⚠️  INVALID WAGER",
                    "Your wager must be a positive whole number of Gems.",
                    COLORS["error"],
                )
            )
            return
        if bet > MAX_SQLITE_INTEGER // JACKPOT_MULTIPLIER:
            await ctx.send(
                embed=build_slots_embed(
                    "⚠️  WAGER TOO LARGE",
                    "That wager exceeds the maximum amount supported by the Gem Vault.",
                    COLORS["error"],
                )
            )
            return

        reels = spin_reels()
        potential_payout, result, won = calculate_payout(reels, bet)
        xp_earned = SPIN_XP + (10 if won else 0) + max(0, potential_payout - bet) // 100

        message = await ctx.send(
            embed=build_slots_embed(
                "🎡  THE REELS ARE SPINNING",
                f"**{ctx.author.mention}**, preparing your **`{bet:,}-Gem`** spin.\n"
                "✨ Good luck!",
                COLORS["win"],
                bet=bet,
                reels=SPIN_FRAMES[0],
            )
        )
        try:
            processed, account, payout = await self.store.play_slots(
                ctx.author.id, bet, potential_payout, xp_earned
            )
        except sqlite3.Error:
            await message.edit(
                embed=build_slots_embed(
                    "⚠️  GEM VAULT UNAVAILABLE",
                    "Your spin could not be processed. No wager was charged. "
                    "Please try again shortly.",
                    COLORS["error"],
                )
            )
            return

        if not processed or account is None:
            balance = account.balance if account else 0
            await message.edit(
                embed=build_slots_embed(
                    "💎  INSUFFICIENT GEMS",
                    f"You need **`{bet:,} Gems`** to spin, but your balance is "
                    f"**`{balance:,} Gems`**.",
                    COLORS["error"],
                    bet=bet,
                    balance=balance,
                )
            )
            return

        await message.edit(
            embed=build_slots_embed(
                "🎡  THE REELS ARE SPINNING",
                f"**{ctx.author.mention}**, the reels are settling...",
                COLORS["win"],
                bet=bet,
                reels=SPIN_FRAMES[1],
            )
        )
        await asyncio.sleep(0.4)

        if result == "jackpot":
            title = "💎  RARE JACKPOT!"
            description = (
                f"👑 **{ctx.author.mention}** discovered the legendary "
                f"**Diamond Prism** combination!\n\n"
                f"🔥 Jackpot payout: **`{payout:,} Gems`**"
            )
            color = COLORS["jackpot"]
        elif result == "triple":
            title = "🏆  PERFECT MATCH!"
            description = (
                f"✨ **{ctx.author.mention}** matched all three reels!\n\n"
                f"**{TRIPLE_MATCH_MULTIPLIER}× wager** secured."
            )
            color = COLORS["win"]
        elif result == "pair":
            title = "✨  PAIR MATCH!"
            description = (
                f"🦊 **{ctx.author.mention}** matched two reels!\n\n"
                f"**{PAIR_MATCH_MULTIPLIER}× wager** secured."
            )
            color = COLORS["win"]
        else:
            title = "🎡  SPIN COMPLETE"
            description = (
                f"**{ctx.author.mention}**, no matching symbols this time.\n\n"
                f"Your wager of **`{bet:,} Gems`** was used."
            )
            color = COLORS["loss"]

        if payout < potential_payout:
            description += (
                "\n\n*The payout was adjusted to fit the maximum supported "
                "Gem balance.*"
            )

        embed = build_slots_embed(
            title,
            description,
            color,
            bet=bet,
            reels=reels,
            payout=payout,
            balance=account.balance,
            level=account.level,
        )
        embed.add_field(
            name="📊  XP EARNED",
            value=f"`{xp_earned:,} XP`",
            inline=True,
        )
        await message.edit(embed=embed)


async def setup(bot: commands.Bot) -> None:
    store = getattr(bot, "gem_store", None)
    if not isinstance(store, GemStore):
        raise RuntimeError("GemStore must be initialized before loading slots_cog.")
    await bot.add_cog(SlotsCog(bot, store))
