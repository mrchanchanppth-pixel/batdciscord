import os
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from gem_store import GemStore

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


async def command_prefix(
    _bot: commands.Bot, message: discord.Message
) -> str:
    typed_prefix = message.content[:4]
    if typed_prefix.casefold() == "sad ":
        return typed_prefix
    return "sad "


class SadBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            case_insensitive=True,
        )
        self.started_at: Optional[datetime] = None
        self.gem_store = GemStore()

    async def setup_hook(self) -> None:
        await self.gem_store.initialize()
        for extension in (
            "game",
            "profile_cog",
            "spam_cog",
            "economy_cog",
            "slots_cog",
            "music_cog",
            "multiplayer_games_cog",
        ):
            await self.load_extension(extension)


client = SadBot()


@client.event
async def on_ready() -> None:
    if client.started_at is None:
        client.started_at = datetime.now(timezone.utc)
    print(f"Logged in as {client.user}")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment or .env file.")

client.run(TOKEN)
