import sqlite3
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands

from gem_store import GemStore


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="you")
    async def you(
        self, ctx: commands.Context, target: Optional[discord.Member] = None
    ) -> None:
        target = target or ctx.author
        created_at = target.created_at.strftime("%b %d, %Y - %H:%M UTC")
        joined_at = (
            target.joined_at.strftime("%b %d, %Y - %H:%M UTC")
            if isinstance(target, discord.Member) and target.joined_at
            else "Unknown"
        )

        embed = discord.Embed(
            title="✨  PLAYER PROFILE",
            description=(
                f"{target.mention}\n"
                "Account details, Gem balance, and server permissions."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👑  USERNAME", value=f"**{target}**", inline=True)
        embed.add_field(name="🆔  USER ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="📅  ACCOUNT CREATED", value=f"`{created_at}`", inline=True)
        embed.add_field(name="📥  SERVER JOINED", value=f"`{joined_at}`", inline=True)

        store = getattr(self.bot, "gem_store", None)
        if isinstance(store, GemStore):
            try:
                account = await store.get_account(target.id)
            except sqlite3.Error:
                embed.add_field(
                    name="💎  GEM VAULT",
                    value="⚠️ Balance temporarily unavailable.",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="💎  GEM BALANCE",
                    value=f"`{account.balance:,} Gems`",
                    inline=True,
                )
                embed.add_field(
                    name="👑  LEVEL",
                    value=f"`{account.level}/100`",
                    inline=True,
                )

        if isinstance(target, discord.Member):
            permissions = target.guild_permissions
            key_permissions = (
                ("👑 Administrator", permissions.administrator),
                ("🛠️ Manage Server", permissions.manage_guild),
                ("🎭 Manage Roles", permissions.manage_roles),
                ("🗂️ Manage Channels", permissions.manage_channels),
                ("👢 Kick Members", permissions.kick_members),
                ("🔨 Ban Members", permissions.ban_members),
                ("🧹 Manage Messages", permissions.manage_messages),
                ("📣 Mention Everyone", permissions.mention_everyone),
            )
            granted = [name for name, enabled in key_permissions if enabled]
            embed.add_field(
                name="🛡️  KEY SERVER PERMISSIONS",
                value="\n".join(f"• {permission}" for permission in granted)
                if granted
                else "*No elevated permissions*",
                inline=False,
            )

        started_at = getattr(self.bot, "started_at", None)
        if started_at:
            elapsed = datetime.now(timezone.utc) - started_at
            total_minutes = int(elapsed.total_seconds() // 60)
            uptime = f"{total_minutes // 60}h {total_minutes % 60}m"
        else:
            uptime = "Starting"
        embed.add_field(name="⚡  BOT UPTIME", value=f"`{uptime}`", inline=True)
        embed.set_footer(
            text="✦ SAD BOT  •  PLAYER INTELLIGENCE",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None,
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.bot.user:
            return
        if self.bot.user not in message.mentions:
            return
        if message.content[:4].casefold() == "sad ":
            return

        embed = discord.Embed(
            title="🤖  SAD BOT COMMAND GUIDE",
            description="Your command center. Select a command to explore its features.",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="✨  PROFILE  •  `sad you [@user]`",
            value="View account metrics, creation/join dates, and key server permissions.",
            inline=False,
        )
        embed.add_field(
            name="💣  MINES  •  `sad um`",
            value="Play 3×3 Mines with Gem stakes, rising payouts, and Cash Out.",
            inline=False,
        )
        embed.add_field(
            name="⚔️  MULTIPLAYER  •  `sad game @user [stake]`",
            value="Challenge a player to Tic-Tac-Toe or Khla Klok.",
            inline=False,
        )
        embed.add_field(
            name="🎡  SLOTS  •  `sad p [amount/all]`",
            value="Spin for matching symbols, Gem payouts, and a rare jackpot.",
            inline=False,
        )
        embed.add_field(
            name="💎  BALANCE  •  `sad bal`",
            value="View your Gem balance and current level.",
            inline=False,
        )
        embed.add_field(
            name="🎁  DAILY CLAIM  •  `sad d`",
            value="Claim 100 Gems once every 24 hours.",
            inline=False,
        )
        embed.add_field(
            name="🤝  TRANSFER  •  `sad pay @user <amount>`",
            value="Transfer Gems securely to another member.",
            inline=False,
        )
        embed.add_field(
            name="👑  PROGRESSION  •  `sad up`",
            value="View your level and XP progression up to Level 100.",
            inline=False,
        )
        embed.add_field(
            name="💬  MENTION",
            value="Single mentions only; repeated mention sequences are disabled.",
            inline=False,
        )
        embed.add_field(
            name="🛑  STOP ALIASES",
            value="`sad chb`  •  `sad stop`  •  `sad chub`  •  `sad chop`",
            inline=False,
        )
        embed.set_footer(text="✦ SAD BOT  •  PREFIX: SAD")
        await message.reply(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))
