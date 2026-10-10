import re
import asyncio
import discord
from discord.ext import commands

MENTION_COMMAND = re.compile(r"^sad\s+<@!?\d+>(?:\s+(\d+))?\s*$", re.IGNORECASE)

def build_notice(title: str, description: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text="✦ SAD BOT  •  COMMUNITY TOOLS")
    return embed


class SpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tasks = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        match = MENTION_COMMAND.fullmatch(message.content.strip())
        if not match or not message.mentions:
            return

        target = message.mentions[0]
        count_text = match.group(1)
        
        try:
            count = int(count_text) if count_text else 1
        except ValueError:
            count = 1

        count = max(1, min(count, 50))

        if message.channel.id in self.active_tasks:
            self.active_tasks[message.channel.id].cancel()

        async def spam_loop():
            try:
                for _ in range(count):
                    await message.channel.send(target.mention)
                    await asyncio.sleep(0.8)
            except asyncio.CancelledError:
                pass
            finally:
                if message.channel.id in self.active_tasks:
                    del self.active_tasks[message.channel.id]

        self.active_tasks[message.channel.id] = asyncio.create_task(spam_loop())

    @commands.command(name="chb", aliases=("stop", "chub", "chop"))
    async def stop(self, ctx: commands.Context) -> None:
        if ctx.channel.id in self.active_tasks:
            self.active_tasks[ctx.channel.id].cancel()
            del self.active_tasks[ctx.channel.id]
            await ctx.send(
                embed=build_notice(
                    "🛑  SPAM STOPPED",
                    "The ongoing mention spam loop has been successfully stopped.",
                    discord.Color.blurple(),
                )
            )
        else:
            await ctx.send(
                embed=build_notice(
                    "🛑  MENTION CONTROL",
                    "There is no active mention spam running in this channel.",
                    discord.Color.blurple(),
                )
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SpamCog(bot))