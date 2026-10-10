import asyncio

import discord
from discord.ext import commands


def voice_embed(
    title: str, description: str, color: discord.Color
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text="✦ SAD BOT  •  MUSIC & VOICE")
    return embed


class MusicCog(commands.Cog):
    @commands.command(name="join")
    @commands.guild_only()
    async def join(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send(
                embed=voice_embed(
                    "⚠️  SERVER ONLY",
                    "This voice command can only be used in a server.",
                    discord.Color.red(),
                )
            )
            return

        voice_state = ctx.author.voice
        if voice_state is None or voice_state.channel is None:
            await ctx.send(
                embed=voice_embed(
                    "🔴  VOICE CHANNEL REQUIRED",
                    "Join a voice channel first, then use **`sad join`**.",
                    discord.Color.red(),
                )
            )
            return

        channel = voice_state.channel
        voice_client = ctx.guild.voice_client
        try:
            if voice_client is None:
                await channel.connect()
                action = "connected to"
            elif voice_client.channel != channel:
                await voice_client.move_to(channel)
                action = "moved to"
            else:
                action = "already connected to"
        except (discord.DiscordException, asyncio.TimeoutError, RuntimeError) as exc:
            embed = voice_embed(
                "🔴  CONNECTION UNAVAILABLE",
                "The bot could not connect to that voice channel. "
                "Check its **Connect** and **Speak** permissions, and ensure "
                "voice support is installed.\n\n"
                f"**Details:** `{exc}`",
                discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        embed = voice_embed(
            "🟢  VOICE CONNECTION READY",
            f"🎧 {action.capitalize()} **{channel.name}**\n"
            f"🎵 Requested by {ctx.author.mention}\n\n"
            "✨ Audio channel access is ready.",
            discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="leave")
    @commands.guild_only()
    async def leave(self, ctx: commands.Context) -> None:
        voice_client = ctx.guild.voice_client
        if voice_client is None:
            await ctx.send(
                embed=voice_embed(
                    "🎧  NO ACTIVE VOICE SESSION",
                    "The bot is not connected to a voice channel in this server.",
                    discord.Color.blurple(),
                )
            )
            return

        channel_name = voice_client.channel.name
        try:
            await voice_client.disconnect()
        except (discord.DiscordException, asyncio.TimeoutError) as exc:
            embed = voice_embed(
                "🔴  DISCONNECT INCOMPLETE",
                "The bot could not leave the voice channel cleanly.\n\n"
                f"**Details:** `{exc}`",
                discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        embed = voice_embed(
            "🔌  VOICE SESSION ENDED",
            f"✅ Disconnected from **{channel_name}**\n"
            "🎵 The bot has left the voice room.",
            discord.Color.from_rgb(90, 100, 125),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicCog())
