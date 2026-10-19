import os
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import DEV_USER_ID, check_background_files, setup_database

load_dotenv()
TOKEN = os.getenv("TOKEN", "").strip()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True


def print_startup_splash(bot_user: str, guild_count: int, sync_count: int, extensions: list[str]):
    pink = "\033[95m"
    cyan = "\033[96m"
    gold = "\033[93m"
    green = "\033[92m"
    bold = "\033[1m"
    reset = "\033[0m"

    ext_str = ", ".join(extensions) if extensions else "None"
    guild_str = f"{guild_count} Connected Server(s)"
    slash_str = f"{sync_count} Command(s) Synced"

    splash = f"""
{pink}         ∧＿∧
       (｡･ω･｡)つ━☆・*。  {bold}{cyan}✨ A R K  B O T  S T U D I O ✨{reset}{pink}
       ⊂/　 /　　  ・゜+   {gold}• Kawaii Anime & Economy Sanctuary •{reset}{pink}
       しーＪ　　   °。+ *´¨)
                     .· ´¸.·*´¨) ¸.·*¨)
                     (¸.·´ (¸.·'* 🌸{reset}

{cyan}  ╔══════════════════════════════════════════════════════════════════════════╗{reset}
{cyan}  ║{reset}  {bold}👑 Lead Developer & Owner :{reset} {gold}Phean Chanthean{reset} ({bold}THEN{reset})                       {cyan}║{reset}
{cyan}  ║{reset}  {bold}⚡ Core Developer         :{reset} {gold}ZERO{reset}                                          {cyan}║{reset}
{cyan}  ║{reset}  {bold}🪄 Systems Developer      :{reset} {gold}VENA{reset}                                          {cyan}║{reset}
{cyan}  ╠══════════════════════════════════════════════════════════════════════════╣{reset}
{cyan}  ║{reset}  {green}●{reset} {bold}Bot Account{reset}    : {bot_user:<48} {cyan}║{reset}
{cyan}  ║{reset}  {green}●{reset} {bold}Admin Servers{reset}  : {guild_str:<48} {cyan}║{reset}
{cyan}  ║{reset}  {green}●{reset} {bold}Slash Commands{reset} : {slash_str:<48} {cyan}║{reset}
{cyan}  ║{reset}  {green}●{reset} {bold}Extensions{reset}     : {ext_str:<48} {cyan}║{reset}
{cyan}  ╚══════════════════════════════════════════════════════════════════════════╝{reset}
"""
    print(splash)


class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self._has_started = False
        self.loaded_extensions = []

    async def setup_hook(self):
        setup_database()
        check_background_files()

        initial_extensions = [
            "cogs.profile",
            "cogs.shop",
            "cogs.economy",
            "cogs.admin",
        ]
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                self.loaded_extensions.append(ext)
                print(f"📦 Loaded extension: {ext}")
            except Exception as e:
                print(f"❌ Failed to load extension {ext}: {e}")
                traceback.print_exc()

    async def on_ready(self):
        try:
            custom_status = discord.CustomActivity(name="✨ AMA nh sad nis tver mix bat sad")
            await self.change_presence(activity=custom_status)
        except Exception:
            activity = discord.Game(name="✨ AMA nh sad nis tver mix bat sad")
            await self.change_presence(activity=activity)

        if not self._has_started:
            self._has_started = True
            sync_count = 0
            try:
                synced = await self.tree.sync()
                sync_count = len(synced)
            except Exception as e:
                print(f"❌ Failed to sync Slash Commands: {e}")

            print_startup_splash(
                bot_user=str(self.user),
                guild_count=len(self.guilds),
                sync_count=sync_count,
                extensions=self.loaded_extensions,
            )

            try:
                dev_user = await self.fetch_user(DEV_USER_ID)
                dm_channel = await dev_user.create_dm()
                async for msg in dm_channel.history(limit=20):
                    if msg.author.id == self.user.id:
                        try:
                            await msg.delete()
                        except Exception:
                            pass

                from cogs.admin import create_dev_startup_embed_and_view
                embed, view = create_dev_startup_embed_and_view(self)
                await dev_user.send(embed=embed, view=view)
            except Exception as e:
                print(f"Failed startup DM cleanup or send: {e}")


bot = ArkBot()

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOKEN is missing. Add TOKEN=your_bot_token to your .env file.")
    bot.run(TOKEN)