import asyncio
import io
import math
import os
import random
import re
import sqlite3
import string
import tempfile
import time
import traceback
import unicodedata
from contextlib import closing
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from premium_borders import PREMIUM_BORDERS, PREMIUM_SHAPES, draw_premium_ring

load_dotenv()
TOKEN = os.getenv("TOKEN", "").strip()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)

profile_lock = asyncio.Lock()
chat_cooldowns = {}
active_spam_tasks = {}

DAILY_REWARD = 10_000
WEEKLY_REWARD = 30_000
DAILY_COOLDOWN = timedelta(days=1)
WEEKLY_COOLDOWN = timedelta(days=7)

DEV_USER_ID = 1083091678312792094
MONEY_EMOJI = "🔷"

SECRET_BG_CODES = {
    "ZERO293847475": "ALL",
    "VENA192983847": "ALL",
    "THEN183874848": "ALL"
}

URL_DEVELOPER = "https://discord.com/users/1083091678312792094"
URL_SUPPORT = "https://thenny.vercel.app/"
URL_FAQ = "https://thenny.vercel.app/#faq"

MEME_QUOTES = [
    {"type": "khmer", "text": "ប៉ិនម៉េស"},
    {"type": "khmer", "text": "ហត់ម៉េស"},
    {"type": "khmer", "text": "លើសម៉េស"},
    {"type": "khmer", "text": "ប៉ិនម៉េសយើងហ្នឹង"},
    {"type": "khmer", "text": "ហត់ម៉េសយើងហ្នឹង"},
    {"type": "khmer", "text": "លើសម៉េសយើងហ្នឹង"},
    {"type": "khmer", "text": "កុំប៉ិនពេក"},
    {"type": "khmer", "text": "លើសហើយណាស់"},
    {"type": "khmer", "text": "អានហើយគេមកវិញអត់"},
    {"type": "khmer", "text": "ស្រឡាញ់គេម្នាក់ឯងហត់អត់"},
    {"type": "khmer", "text": "ស្រឡាញ់ខ្លួនឯងអត់ហត់ដូចស្រឡាញ់គេម្នាក់ឯងទេ"},
    {"type": "khmer", "text": "ស្រឡាញ់គេម្នាក់ឯងមធ្យមងំគិតថាគេស្រឡាញ់យើងវិញទៀត"},
    {"type": "khmer", "text": "បានហើយឈប់ស្រឡាញ់គេម្នាក់ឯងទៅ"},
    {"type": "khmer", "text": "ញ៉ាំបាយនៅ ? ធ្វើអីហ្នឹងសុំនិយាយជាមួយបានអត់"},
    {"type": "khmer", "text": "យើងហ្នឹងធ្វើអីដឹងខ្លួនឯងហើយ"},
    {"type": "khmer", "text": "អរុណសួស្ដីមនុស្សដែលគ្មានសមត្ថភាពទទួលបានពាក្យ good morning ពីគេ"},
    {"type": "khmer", "text": "ខ្ញុំអស់លុយចាយហើយ"},
    {"type": "khmer", "text": "ខ្ញុំហេវបាយខ្លាំងណាស់"},
    {"type": "khmer", "text": "គេអត់មកវិញទេឈប់គិតពីគេទៀតទៅណាស់ក្មេងតូច"},
    {"type": "khmer", "text": "បើអ្នកពិបាកចិត្តមែនទេនេះថ្នាំញៀនអាចជួយអ្នកได้"},
    {"type": "khmer", "text": "កុំចង់លេងជាមួយសាក់ដា"},
    {"type": "khmer", "text": "ជីវិតនេះតស៊ូណាស់តែអត់សូវមានលុយទេ"},
    {"type": "khmer", "text": "ឈប់សាងការចងចាំជាមួយមនុស្សដែលគេមិនខ្វល់ពីយើងទៀតទៅ"},
    {"type": "khmer", "text": "ញញឹមដាក់គេតែក្នុងចិត្តយំសោកសង្រេង"},
    {"type": "khmer", "text": "គេមិនបានស្រឡាញ់យើងទេគេគ្រាន់តែអផ្សុក"},
    {"type": "khmer", "text": "កុំសួរច្រើនពេកឈឺក្បាលណាស់"},
    {"type": "khmer", "text": "ចង់គេចចេញពីពិភពលោកមួយនេះភ្លាមៗ"},
    {"type": "khmer", "text": "ប្រាប់ហើយថាកុំឈរមើលមុខយូរពេកក្រែងលោស្រឡាញ់បាត់"},
    {"type": "khmer", "text": "ថ្ងៃនេះអត់សូវស្រួលខ្លួនទេ សុំលុយចាយ ១ ម៉ឺនមក"},
    {"type": "khmer", "text": "អ្នកខ្លះកើតមកដើម្បីធ្វើឱ្យយើងខកចិត្ត"},
    {"type": "khmer", "text": "ញ៉ាំទឹកច្រើនៗផងក្រែងលោជួយបានខ្លះ"},
    {"type": "khmer", "text": "គេមិនខ្វល់ពីយើងទេបងប្អូនអើយ"},
    {"type": "khmer", "text": "ដេកលក់ស្រួលជាងគិតរឿងអត់ប្រយោជន៍"},
    {"type": "khmer", "text": "តស៊ូឡើងក្មេងតូចផ្លូវខាងមុខនៅវែងឆ្ងាយណាស់"},
    {"type": "khmer", "text": "កុំយំអីអូនអើយ យំទៅក៏គេមិនមកវិញដែរ"},
    {"type": "khmer", "text": "ស៊ូៗឡើងកុំបោះបង់រឿងក្តីស្រមៃ"},
    {"type": "khmer", "text": "ពេលខ្លះស្ងៀមស្ងាត់គឺជាចម្លើយที่ดีที่สุด"},
    {"type": "khmer", "text": "កុំខ្វល់សម្តីអ្នកដទៃពេកជីវិតយើងទេ"},
    {"type": "khmer", "text": "ញញឹមឡើងទោះបីជាពិបាកយ៉ាងណាក៏ដោយ"},
    {"type": "khmer", "text": "មិនបាច់មកខ្វល់ពីខ្ញុំទេខ្ញុំនៅរស់បាន"},
    {"type": "bilingual", "en": "Emotional Damage!", "kh": "ការខូចខាតផ្លូវចិត្តធ្ងន់ធ្ងរ!"},
    {"type": "bilingual", "en": "Why are you running?! Why are you running?!", "kh": "រត់ធ្វើអី?! រត់ធ្វើអី?!"},
    {"type": "bilingual", "en": "Bro really thought he was the main character.", "kh": "ស្មានតែខ្លួនឯងជាតួឯកមែនហ្នឹង?"},
    {"type": "bilingual", "en": "Absolute cinema!", "kh": "សម្តែងបានល្អឥតខ្ចោះ ដូចក្នុងកុន!"},
    {"type": "bilingual", "en": "Hold up, let him cook!", "kh": "ចាំបន្តិចមើល៍ ទុកឱ្យគាត់សម្តែងឱ្យចប់សិន!"},
    {"type": "bilingual", "en": "NPC behavior detected.", "kh": "ធ្វើចរិតដូចតួអង្គ NPC ក្នុងហ្គេមចឹង។"},
    {"type": "bilingual", "en": "Task failed successfully.", "kh": "បំពេញភារកិច្ចបរាជ័យដោយជោគជ័យ។"},
    {"type": "bilingual", "en": "Outstanding move!", "kh": "ជាក្បាច់វាយលុកដ៏អស្ចារ្យ!"}
]

class StandardLinksView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ, row=2))


class BalDirectShopView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛍️ Shop", url=URL_DEVELOPER))


# ---------------------------------------------------------------------------
# 🚀 SLASH COMMAND: /update (Premium Developer Dashboard & Management Panel)
# ---------------------------------------------------------------------------
@tree.command(name="update", description="✨ Open the bot startup premium dashboard and management panel")
async def update_command(interaction: discord.Interaction):
    if interaction.user.id != DEV_USER_ID:
        return await interaction.response.send_message("❌ Sorry! This command is only available for the Developer.", ephemeral=True)
    
    if interaction.guild is not None:
        return await interaction.response.send_message("🔒 This command can only be used in **Private DMs**!", ephemeral=True)

    embed, view = create_dev_startup_embed_and_view(interaction.client)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CustomWelcomeNoteModal(discord.ui.Modal, title="✨ Send Custom Welcome Announcement"):
    note_input = discord.ui.TextInput(
        label="Enter Welcome Note Message",
        placeholder="Type your custom announcement message here...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(self, guild, admin_user, client_ref):
        super().__init__()
        self.guild = guild
        self.admin_user = admin_user
        self.client_ref = client_ref

    async def on_submit(self, interaction: discord.Interaction):
        card_filename = "welcome_card.png"
        try:
            avatar_bytes = await self.admin_user.display_avatar.with_size(512).read()
            await asyncio.to_thread(
                generate_welcome_card,
                avatar_bytes,
                self.admin_user.display_name,
                self.guild.name,
                card_filename
            )
            
            custom_note = self.note_input.value.strip()
            embed = discord.Embed(
                title=f"🌸 Welcome to {self.guild.name}!",
                description=f"Hello {self.admin_user.mention}!\n\n{custom_note}\n\n*— Sent with love by Developer Phean Chanthean*",
                color=discord.Color.from_rgb(147, 112, 219)
            )
            embed.set_image(url=f"attachment://{card_filename}")

            file = discord.File(card_filename, filename=card_filename)
            await self.admin_user.send(embed=embed, file=file, view=StandardLinksView())
            
            await interaction.response.send_message(f"✅ DM sent successfully to **{self.admin_user}** (`{self.guild.name}`)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ DM failed: {e}", ephemeral=True)
        finally:
            if os.path.exists(card_filename):
                os.remove(card_filename)


class AdminSelectForDM(discord.ui.Select):
    def __init__(self, guild, client_ref):
        self.guild = guild
        self.client_ref = client_ref
        options = []
        admins = []
        if guild.owner:
            admins.append(guild.owner)
        for m in guild.members:
            if m.guild_permissions.administrator and m not in admins and not m.bot:
                admins.append(m)
        
        for admin in admins[:25]:
            role_type = "Owner 👑" if admin == guild.owner else "Administrator 🛡️"
            options.append(discord.SelectOption(
                label=f"{admin.display_name} ({admin.name})"[:100],
                value=str(admin.id),
                description=f"Role: {role_type}"[:100]
            ))
        
        if not options:
            options.append(discord.SelectOption(label="No admin found", value="none"))

        super().__init__(placeholder="🛡️ Select Admin or Owner to DM...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        if self.values[0] == "none":
            return await interaction.response.send_message("⚠️ No valid admin found.", ephemeral=True)

        admin_id = int(self.values[0])
        admin_user = self.guild.get_member(admin_id) or await interaction.client.fetch_user(admin_id)

        if not admin_user:
            return await interaction.response.send_message("❌ Could not fetch admin user.", ephemeral=True)

        await interaction.response.send_modal(CustomWelcomeNoteModal(self.guild, admin_user, self.client_ref))


class AdminSelectView(discord.ui.View):
    def __init__(self, guild, client_ref):
        super().__init__(timeout=300)
        self.guild = guild
        self.client_ref = client_ref
        self.add_item(AdminSelectForDM(guild, client_ref))

    @discord.ui.button(label="🔙 Back to Server List", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_servers(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        embed, view = create_dev_startup_embed_and_view(self.client_ref)
        await interaction.response.edit_message(embed=embed, view=view)


class ServerSelect(discord.ui.Select):
    def __init__(self, guilds):
        options = []
        for g in guilds[:25]:
            desc = f"Owner: {g.owner} | Members: {g.member_count}"
            options.append(discord.SelectOption(label=g.name[:100], value=str(g.id), description=desc[:100]))
        
        super().__init__(placeholder="🌐 Select a server to manage...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        guild_id = int(self.values[0])
        guild = interaction.client.get_guild(guild_id)
        
        if not guild:
            return await interaction.response.send_message("❌ Server not found.", ephemeral=True)

        online_count = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
        bot_count = sum(1 for m in guild.members if m.bot)
        human_count = guild.member_count - bot_count

        embed = discord.Embed(
            title=f"📊 Server Details: {guild.name}",
            description=f"**Server ID:** `{guild.id}`\n**Owner:** `{guild.owner}`\n**Created At:** `{guild.created_at.strftime('%Y-%m-%d')}`",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.add_field(name="👑 Server Owner", value=f"{guild.owner.mention} (`{guild.owner}`)", inline=False)
        embed.add_field(name="👥 Total Members", value=f"`{guild.member_count:,}`", inline=True)
        embed.add_field(name="🧑 Humans", value=f"`{human_count:,}`", inline=True)
        embed.add_field(name="🤖 Bots", value=f"`{bot_count:,}`", inline=True)
        embed.add_field(name="🟢 Online", value=f"`~{online_count:,}`", inline=True)
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.set_footer(text="✨ Choose an action below to proceed.")

        view = ServerManagementView(guild.id, interaction.client)
        await interaction.response.edit_message(embed=embed, view=view)


class ServerManagementView(discord.ui.View):
    def __init__(self, guild_id, client_ref):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.client_ref = client_ref

    @discord.ui.button(label="📩 Send DM to Admin/Owner", style=discord.ButtonStyle.primary, row=0)
    async def dm_admin_prompt(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        guild = self.client_ref.get_guild(self.guild_id)
        if not guild:
            return await interaction.response.send_message("❌ Server not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"🌸 Select Admin/Owner in {guild.name}",
            description="Select an administrator from the dropdown menu to send a customized welcome DM.",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        view = AdminSelectView(guild, self.client_ref)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🚪 Leave Server", style=discord.ButtonStyle.danger, row=0)
    async def leave_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        guild = self.client_ref.get_guild(self.guild_id)
        if not guild:
            return await interaction.response.send_message("⚠️ Bot has already left this server.", ephemeral=True)

        guild_name = guild.name
        try:
            await guild.leave()
            for child in self.children:
                child.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = f"🚪 Left Server: {guild_name}"
            
            new_view = DevDashboardView(self.client_ref.guilds, self.client_ref.user.id, client_ref=self.client_ref)
            await interaction.message.edit(embed=embed, view=new_view)
            await interaction.response.send_message(f"✅ Successfully left server **{guild_name}**!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to leave server: {e}", ephemeral=True)

    @discord.ui.button(label="🔙 Back to Server List", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        embed, view = create_dev_startup_embed_and_view(self.client_ref)
        await interaction.response.edit_message(embed=embed, view=view)


class DevDashboardView(discord.ui.View):
    def __init__(self, guilds, client_id, client_ref=None):
        super().__init__(timeout=300)
        self.client_ref = client_ref
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot"
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="➕ Add Server", url=invite_url))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ))
        
        if guilds:
            self.add_item(ServerSelect(guilds))

    @discord.ui.button(label="📖 Command Guide", style=discord.ButtonStyle.success, row=3)
    async def show_help_guide(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)

        help_embed = discord.Embed(
            title="📖 Complete Command Reference",
            description=(
                "Below is the full list of available commands.\n"
                "All commands use the **`a`** prefix unless stated otherwise.\n"
                "─────────────────────────────"
            ),
            color=discord.Color.from_rgb(147, 112, 219),
        )
        help_embed.add_field(
            name="💰 Economy & Wallet",
            value=(
                "`abal` — View your Coins, Bank & AAA balance\n"
                "`ad` — Claim your daily reward (10,000 Coins)\n"
                "`aw` — Claim your weekly reward (30,000 Coins)\n"
                "`ajol <amount|all>` — Deposit Coins into your Bank\n"
                "`ajenh <amount|all>` — Withdraw Coins from your Bank"
            ),
            inline=False,
        )
        help_embed.add_field(
            name="🗡️ Robbery System",
            value=(
                "`aoy @user` — Attempt to rob a user's cash\n"
                "`aoyyg @user` — Same as `aoy` (alias)\n"
                "• 60% chance of success, steal 5–25% of their cash\n"
                "• Caught? You pay 5–15% of *your* cash to the victim\n"
                "• Bank funds are safe from robbery"
            ),
            inline=False,
        )
        help_embed.add_field(
            name="🖼️ Profile & Customization",
            value=(
                "`aup` or `ap` — View your profile card\n"
                "`aup @user` — View another user's profile card\n"
                "`ashop` or `ash` — Open the Background & Border Shop\n"
                "• Browse, preview, buy & equip backgrounds\n"
                "• Purchase with **4,000,000 Coins** or **30 AAA**"
            ),
            inline=False,
        )
        help_embed.add_field(
            name="🎲 Mystery Codes & Promo",
            value=(
                "`arkcode` — Open the Mystery Code Shop\n"
                "• Buy codes (1M each), redeem for random rewards\n"
                "• Win rare backgrounds, AAA items, or mega coins\n"
                "`aaddcode` — Redeem a secret promo code"
            ),
            inline=False,
        )
        help_embed.add_field(
            name="😂 Fun & Social",
            value=(
                "`hi` — Say hello to the bot\n"
                "`ako @user` — Send a random meme quote\n"
                "`@bot` — Mention the bot for a random quote\n"
                "`aps @user <count> <text>` — Mention-loop a user\n"
                "`astop` — Stop an active mention loop"
            ),
            inline=False,
        )
        help_embed.add_field(
            name="🔐 Developer Only",
            value=(
                "`/update` — Open this dashboard (DM only)\n"
                "`acode` — View secret promo codes console\n"
                "`aadp <amount>` — Add Coins to yourself\n"
                "`aadp @user <amount>` — Add Coins to a user\n"
                "`aadp bank <amount>` — Add to Bank balance\n"
                "`aadp AAA <count>` — Add AAA items\n"
                "• Supports `K` / `M` / `B` / `T` suffixes"
            ),
            inline=False,
        )
        help_embed.set_footer(text="Ark Bot • Premium Command Reference")
        await interaction.response.send_message(embed=help_embed, ephemeral=True)

    @discord.ui.button(label="🔙 Refresh Dashboard", style=discord.ButtonStyle.secondary, row=3)
    async def refresh_dashboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != DEV_USER_ID:
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        if self.client_ref:
            embed, view = create_dev_startup_embed_and_view(self.client_ref)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("⚠️ Cannot refresh — client reference unavailable.", ephemeral=True)


class AdminActionApprovalView(discord.ui.View):
    def __init__(self, dev_id, target_user_id, amount, is_item, item_count, is_bank=False):
        super().__init__(timeout=180)
        self.dev_id = dev_id
        self.target_user_id = target_user_id
        self.amount = amount
        self.is_item = is_item
        self.item_count = item_count
        self.is_bank = is_bank

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        if self.is_item:
            add_special_item(self.target_user_id, self.item_count)
            msg = f"✅ Successfully added **{self.item_count:,}** AAA items to user ID `{self.target_user_id}`!"
        elif self.is_bank:
            add_bank_balance(self.target_user_id, self.amount)
            msg = f"✅ Successfully added **{MONEY_EMOJI} {self.amount:,}** to Bank of user ID `{self.target_user_id}`!"
        else:
            add_balance(self.target_user_id, self.amount)
            msg = f"✅ Successfully added **{MONEY_EMOJI} {self.amount:,}** to Cash of user ID `{self.target_user_id}`!"

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✨ ADMIN ACTION: ACCEPTED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ ADMIN ACTION: CANCELLED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("⚠️ Admin action cancelled.", ephemeral=True)


class AcodeApprovalView(discord.ui.View):
    def __init__(self, dev_id, embed_data, client_ref):
        super().__init__(timeout=180)
        self.dev_id = dev_id
        self.embed_data = embed_data
        self.client_ref = client_ref

    @discord.ui.button(label="Execute", style=discord.ButtonStyle.success, emoji="✅")
    async def execute_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✨ ACODE EXECUTED & POSTED TO DM"
        await interaction.message.edit(embed=embed, view=self)

        try:
            dev_user = await self.client_ref.fetch_user(self.dev_id)
            await dev_user.send(embed=self.embed_data)
            await interaction.response.send_message("✅ Successfully posted to your DM!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send DM: {e}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ ACODE CANCELLED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("⚠️ Action cancelled.", ephemeral=True)


class SecretCodeApprovalView(discord.ui.View):
    def __init__(self, dev_id, target_user_id, code, client_ref):
        super().__init__(timeout=300)
        self.dev_id = dev_id
        self.target_user_id = target_user_id
        self.code = code
        self.client_ref = client_ref

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_redeem(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        try:
            for bg_code in BACKGROUNDS.keys():
                if bg_code != DEFAULT_BG:
                    unlock_specific_background(self.target_user_id, bg_code)

            target_user = await self.client_ref.fetch_user(self.target_user_id)
            if target_user:
                success_embed = discord.Embed(
                    title="🔥 UNLOCK ALL BACKGROUNDS APPROVED!",
                    description=f"Congratulations! Developer approved your code `{self.code}`. **All Exclusive Backgrounds** have been unlocked! Use `ashop` to equip them.",
                    color=discord.Color.gold()
                )
                success_embed.set_thumbnail(url=target_user.display_avatar.url)
                await target_user.send(embed=success_embed)

            for child in self.children:
                child.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✨ SECRET CODE: APPROVED & UNLOCKED"
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.send_message(f"✅ Successfully approved code for user ID `{self.target_user_id}`!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_redeem(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
        
        try:
            target_user = await self.client_ref.fetch_user(self.target_user_id)
            if target_user:
                fail_embed = discord.Embed(
                    title="❌ UNLOCK ALL BACKGROUNDS REJECTED",
                    description=f"Sorry, your submitted code `{self.code}` was rejected by the developer.",
                    color=discord.Color.red()
                )
                await target_user.send(embed=fail_embed)
        except Exception:
            pass

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ SECRET CODE: REJECTED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("⚠️ Request rejected.", ephemeral=True)


class SecretCodeModal(discord.ui.Modal, title="🔑 Redeem Secret Promo Code"):
    code_input = discord.ui.TextInput(
        label="Enter Secret Promo Code",
        placeholder="Type code here...",
        required=True,
        max_length=50
    )

    def __init__(self, client_ref):
        super().__init__()
        self.client_ref = client_ref

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        entered_code = self.code_input.value.strip().upper()
        
        if entered_code not in SECRET_BG_CODES:
            embed = discord.Embed(
                title="❌ Invalid Promo Code",
                description="The secret code entered is invalid or expired.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            dev_user = await self.client_ref.fetch_user(DEV_USER_ID)
            if dev_user:
                req_embed = discord.Embed(
                    title="🔑 NEW SECRET CODE REDEEM REQUEST",
                    description=(
                        f"**User:** {user.mention} (`{user}`)\n"
                        f"**User ID:** `{user.id}`\n"
                        f"**Submitted Code:** `{entered_code}`\n\n"
                        "Click **Accept** below to unlock all backgrounds for this user, or **Cancel** to reject."
                    ),
                    color=discord.Color.from_rgb(147, 112, 219)
                )
                req_embed.set_thumbnail(url=user.display_avatar.url)
                req_embed.set_footer(text=f"Requested by {user.display_name}", icon_url=user.display_avatar.url)
                
                view = SecretCodeApprovalView(DEV_USER_ID, user.id, entered_code, self.client_ref)
                await dev_user.send(embed=req_embed, view=view)

            embed = discord.Embed(
                title="⏳ Request Sent to Developer",
                description=f"Your code `{entered_code}` has been submitted for developer verification! You will be notified once approved.",
                color=discord.Color.from_rgb(147, 112, 219)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send request to developer: {e}", ephemeral=True)


class SecretCodeView(discord.ui.View):
    def __init__(self, client_ref):
        super().__init__(timeout=180)
        self.client_ref = client_ref

    @discord.ui.button(label="🔑 Redeem Code", style=discord.ButtonStyle.success)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SecretCodeModal(self.client_ref))


class RedeemCodeModal(discord.ui.Modal, title="🎁 Redeem Mystery Code"):
    code_input = discord.ui.TextInput(
        label="Enter Your Mystery Code",
        placeholder="Type code here...",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        random_code = self.code_input.value.strip().upper()
        
        if not random_code:
            return await interaction.response.send_message("⚠️ Please enter a valid code!", ephemeral=True)

        roll = random.random()

        if roll < 0.03:
            reward_bg_code = random.choice(list(BACKGROUNDS.keys()))
            reward_name = BACKGROUNDS[reward_bg_code]['name']
            unlock_specific_background(user_id, reward_bg_code)
            embed = discord.Embed(
                title="🔥 MYSTERY REWARD: RARE BACKGROUND",
                description=f"Code: `{random_code}`\n\nYou won background: **{reward_name}**!",
                color=discord.Color.gold()
            )
        elif roll < 0.08:
            add_special_item(user_id, 1)
            embed = discord.Embed(
                title="💎 MYSTERY REWARD: SPECIAL ITEM",
                description=f"Code: `{random_code}`\n\nYou won **1** AAA item!",
                color=discord.Color.purple()
            )
        elif roll < 0.45:
            coins_won = random.randint(100_000, 10_000_000)
            add_balance(user_id, coins_won)
            embed = discord.Embed(
                title="💰 MYSTERY REWARD: COINS",
                description=f"Code: `{random_code}`\n\nYou won **{MONEY_EMOJI} {coins_won:,}** coins!",
                color=discord.Color.green()
            )
        else:
            coins_won = random.randint(10_000, 50_000)
            add_balance(user_id, coins_won)
            embed = discord.Embed(
                title="🎁 MYSTERY REWARD: BONUS",
                description=f"Code: `{random_code}`\n\nYou won **{MONEY_EMOJI} {coins_won:,}** bonus coins!",
                color=discord.Color.blurple()
            )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Redeemed by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BuyCodeQuantityModal(discord.ui.Modal, title="🎲 Buy Mystery Code"):
    qty_input = discord.ui.TextInput(
        label="Enter Quantity (1 Code = 1,000,000 Coins)",
        placeholder="e.g. 1, 2, 3...",
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        try:
            qty = int(self.qty_input.value.strip())
            if qty <= 0:
                raise ValueError()
        except ValueError:
            return await interaction.response.send_message("❌ Please enter a valid positive number!", ephemeral=True)

        price_per_code = 1_000_000
        total_price = price_per_code * qty

        balance, bank, xp, level, chat_xp, voice_xp, aa_count = get_user_data(user_id)

        if balance < total_price:
            return await interaction.response.send_message(
                f"❌ Insufficient cash! You need **{MONEY_EMOJI} {total_price:,}** for **{qty}** code(s), but you only have **{MONEY_EMOJI} {balance:,}**.",
                ephemeral=True
            )

        deduct_balance(user_id, total_price)

        generated_codes = []
        for _ in range(qty):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=15))
            generated_codes.append(code)

        codes_str = "\n".join([f"• `{c}`" for c in generated_codes])
        embed = discord.Embed(
            title=f"🛒 Successfully Purchased {qty} Code(s)!",
            description=f"You spent **{MONEY_EMOJI} {total_price:,}**.\n\nHere are your generated codes:\n{codes_str}\n\n*Click 'Redeem Code' button to use them!*",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Buyer: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ArkCodeDashboardView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="🛒 Buy Code", style=discord.ButtonStyle.primary, emoji="🎲")
    async def buy_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("⚠️ This session is not yours!", ephemeral=True)
        await interaction.response.send_modal(BuyCodeQuantityModal())

    @discord.ui.button(label="🎁 Redeem Code", style=discord.ButtonStyle.success, emoji="🔑")
    async def redeem_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("⚠️ This session is not yours!", ephemeral=True)
        await interaction.response.send_modal(RedeemCodeModal())


def create_dev_startup_embed_and_view(client_ref):
    guilds = client_ref.guilds
    total_members = sum(g.member_count for g in guilds)
    total_bots = sum(1 for g in guilds for m in g.members if m.bot)
    total_humans = total_members - total_bots

    # Sort servers by member count descending for the top-servers list
    top_guilds = sorted(guilds, key=lambda g: g.member_count, reverse=True)[:5]
    top_list = "\n".join(
        f"> `{i+1}.` **{g.name}** — `{g.member_count:,}` members"
        for i, g in enumerate(top_guilds)
    )

    embed = discord.Embed(
        title="⚡ PREMIUM DEVELOPER DASHBOARD",
        description=(
            "```\n"
            "  Bot Status: ● ONLINE & OPERATIONAL\n"
            "```\n"
            "Welcome back, Developer. All systems are running normally.\n"
            "Use the dropdown below to manage servers, or tap **📖 Command Guide** for the full reference."
        ),
        color=discord.Color.from_rgb(147, 112, 219),
    )
    embed.add_field(
        name="📊 Global Statistics",
        value=(
            f"🌐  **Servers:** `{len(guilds)}`\n"
            f"👥  **Total Members:** `{total_members:,}`\n"
            f"🧑  **Humans:** `{total_humans:,}`\n"
            f"🤖  **Bots:** `{total_bots:,}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🛒 Shop Catalog",
        value=(
            f"🖼️  **Backgrounds:** `{len(BACKGROUNDS)}`\n"
            f"✨  **Borders:** `{len(AVATAR_BORDERS)}`\n"
            f"💎  **BG Price:** `4,000,000` / `30 AAA`\n"
            f"💎  **Border Price:** `4,000,000` / `30 AAA`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🏆 Top Servers",
        value=top_list if top_list else "> No servers connected.",
        inline=False,
    )
    embed.add_field(
        name="⚙️ Quick Actions",
        value=(
            "▸ **Select a server** from the dropdown to manage it\n"
            "▸ **📖 Command Guide** — View all bot commands\n"
            "▸ **🔙 Refresh** — Reload dashboard statistics\n"
            "▸ **➕ Add Server** — Invite the bot to a new server"
        ),
        inline=False,
    )
    embed.set_footer(text="Ark Bot • Premium Dashboard • Developed by Phean Chanthean")

    view = DevDashboardView(guilds, client_ref.user.id, client_ref=client_ref)
    return embed, view


def setup_database():
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    bank INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_daily TEXT,
                    last_weekly TEXT,
                    last_work TEXT,
                    chat_xp INTEGER DEFAULT 0,
                    voice_xp INTEGER DEFAULT 0,
                    aa_item INTEGER DEFAULT 0,
                    active_bg TEXT DEFAULT 'bg1'
                )
            """)
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(users)")
            }
            if "bank" not in existing_columns:
                connection.execute("ALTER TABLE users ADD COLUMN bank INTEGER DEFAULT 0")
            if "aa_item" not in existing_columns:
                connection.execute("ALTER TABLE users ADD COLUMN aa_item INTEGER DEFAULT 0")
            ensure_background_columns(connection)
            _ensure_rob_column(connection)


def get_user_data(user_id):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            cursor = connection.execute(
                "SELECT balance, bank, xp, level, chat_xp, voice_xp, aa_item FROM users WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()


def deduct_balance(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))


def add_balance(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            connection.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))


def add_bank_balance(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            connection.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, user_id))


def add_special_item(user_id, count):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            connection.execute("UPDATE users SET aa_item = aa_item + ? WHERE user_id = ?", (count, user_id))


def deposit_to_bank(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            bal = connection.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            if amount == "all":
                amount = bal
            else:
                amount = int(amount)
            
            if amount <= 0 or bal < amount:
                return False, bal, "Insufficient cash on hand!"

            connection.execute("UPDATE users SET balance = balance - ?, bank = bank + ? WHERE user_id = ?", (amount, amount, user_id))
            return True, amount, "Deposit successful!"


def withdraw_from_bank(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            bank = connection.execute("SELECT bank FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            if amount == "all":
                amount = bank
            else:
                amount = int(amount)

            if amount <= 0 or bank < amount:
                return False, bank, "Insufficient bank balance!"

            connection.execute("UPDATE users SET balance = balance + ?, bank = bank - ? WHERE user_id = ?", (amount, amount, user_id))
            return True, amount, "Withdrawal successful!"


def add_chat_xp(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                "SELECT xp, level, chat_xp FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            xp, level, chat_xp = row[0], row[1], row[2]
            
            new_chat_xp = chat_xp + amount
            new_total_xp = xp + amount
            new_level = level
            while new_total_xp >= new_level * 500:
                new_level += 1

            connection.execute(
                "UPDATE users SET xp = ?, level = ?, chat_xp = ? WHERE user_id = ?",
                (new_total_xp, new_level, new_chat_xp, user_id),
            )


def add_voice_xp(user_id, amount):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                "SELECT xp, level, voice_xp FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            xp, level, voice_xp = row[0], row[1], row[2]
            
            new_voice_xp = voice_xp + amount
            new_total_xp = xp + amount
            new_level = level
            while new_total_xp >= new_level * 500:
                new_level += 1

            connection.execute(
                "UPDATE users SET xp = ?, level = ?, voice_xp = ? WHERE user_id = ?",
                (new_total_xp, new_level, new_voice_xp, user_id),
            )


def claim_reward(user_id, column, reward, cooldown):
    if column not in ("last_daily", "last_weekly"):
        raise ValueError("Invalid claim column")

    now = datetime.now(timezone.utc)
    with closing(sqlite3.connect("database.db")) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            row = connection.execute(
                f"SELECT {column} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            last_claim_text = row[0]

            last_claim = datetime.fromisoformat(last_claim_text) if last_claim_text else None
            if last_claim is not None:
                next_claim = last_claim + cooldown
                if now < next_claim:
                    connection.rollback()
                    return False, next_claim - now

            connection.execute(
                f"UPDATE users SET balance = balance + ?, {column} = ? WHERE user_id = ?",
                (reward, now.isoformat(), user_id),
            )
            new_balance = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
            connection.commit()
            return True, new_balance
        except Exception:
            connection.rollback()
            raise


BACKGROUNDS = {
    "bg1": {"name": "✨ Default Genesis", "price": 0, "filename": "bdg1.png"},
    "bg2": {"name": "🌸 Sakura Spirit", "price": 4_000_000, "filename": "bdg2.png"},
    "bg3": {"name": "⚡ Cyber Neon Boy", "price": 4_000_000, "filename": "bdg3.png"},
    "bg4": {"name": "👑 Lunox Eclipse", "price": 4_000_000, "filename": "bdg4.png"},
    "bg5": {"name": "🍃 Angola Mystic Elf", "price": 4_000_000, "filename": "bdg5.png"},
    "bg6": {"name": "💫 Princess Aurelia", "price": 4_000_000, "filename": "bdg6.png"},
    "bg7": {"name": "💎 Royal Seraphim", "price": 4_000_000, "filename": "bdg7.png"},
    "bg8": {"name": "🦋 Fairy Celestia", "price": 4_000_000, "filename": "bdg8.png"},
    "bg9": {"name": "🌧️ Melancholy Soul", "price": 4_000_000, "filename": "bdg9.png"},
    "bg10": {"name": "🔮 Infinite Gojo", "price": 4_000_000, "filename": "bdg10.png"},
    "bg11": {"name": "🌟 Layla Starlight", "price": 4_000_000, "filename": "bdg11.png"},
    "bg12": {"name": "⛏️ Blockland Universe", "price": 4_000_000, "filename": "bdg12.png"},
    "bg13": {"name": "👘 Kimono Blossom", "price": 4_000_000, "filename": "bdg13.png"},
    "bg14": {"name": "🔥 Changli Inferno", "price": 4_000_000, "filename": "bdg14.png"},
    "bg15": {"name": "🗡️ Dark Knight", "price": 4_000_000, "filename": "bdg15.png"},
    "bg16": {"name": "👻 Phantom Blade", "price": 4_000_000, "filename": "bdg16.png"},
    "bg17": {"name": "🌀 Mystic Realm", "price": 4_000_000, "filename": "bdg17.png"},
    "bg18": {"name": "🪐 Astral Horizon", "price": 4_000_000, "filename": "bdg18.png"},
    "bg19": {"name": "❄️ Frozen Requiem", "price": 4_000_000, "filename": "bdg19.png"},
    "bg20": {"name": "🐉 Dragon Sovereign", "price": 4_000_000, "filename": "bdg20.png"},
    "bg21": {"name": "🌙 Lunar Veil", "price": 4_000_000, "filename": "bdg21.png"},
    "bg22": {"name": "⚔️ Crimson Warlord", "price": 4_000_000, "filename": "bdg22.png"},
    "bg23": {"name": "💀 Shadow Monarch", "price": 4_000_000, "filename": "bdg23.png"},
}
DEFAULT_BG = "bg1"
BACKGROUND_COIN_PRICE = 4_000_000
BACKGROUND_AAA_PRICE = 30
BORDER_COIN_PRICE = 4_000_000
BORDER_AAA_PRICE = 30
DEFAULT_BORDER = "default"

# Five paid avatar-ring styles. Each has its own SHAPE (see _draw_avatar_ring), gradient and glow.
AVATAR_BORDERS = {
    "ring1": {"name": "🌌 Aurora Pulse", "shape": "double", "start": (90, 220, 255, 255), "end": (135, 90, 255, 255), "glow": (80, 150, 255, 175), "glow_blur": 22, "glow_spread": 14},
    "ring2": {"name": "🔥 Solar Flare", "shape": "rays", "start": (255, 85, 65, 255), "end": (255, 190, 70, 255), "glow": (255, 95, 50, 175), "glow_blur": 20, "glow_spread": 22},
    "ring3": {"name": "🌿 Emerald Mist", "shape": "dashed", "start": (50, 245, 160, 255), "end": (20, 150, 115, 255), "glow": (40, 220, 150, 165), "glow_blur": 30, "glow_spread": 20},
    "ring4": {"name": "🌸 Sakura Dream", "shape": "orbs", "start": (255, 115, 195, 255), "end": (185, 125, 255, 255), "glow": (255, 105, 205, 170), "glow_blur": 24, "glow_spread": 18},
    "ring5": {"name": "💎 Royal Gold", "shape": "royal", "start": (255, 225, 100, 255), "end": (255, 145, 55, 255), "glow": (255, 195, 70, 180), "glow_blur": 18, "glow_spread": 14},
}


# 10 premium borders (ring6..ring15) are defined in premium_borders.py and ADDED to the shop here.
AVATAR_BORDERS.update(PREMIUM_BORDERS)


def border_prices(code):
    """(coins, AAA) price of an avatar border. Defaults to the standard 4,000,000 / 30."""
    info = AVATAR_BORDERS.get(code, {})
    return info.get("coins", BORDER_COIN_PRICE), info.get("aaa", BORDER_AAA_PRICE)


def normalize_bg_code(raw):
    code = str(raw).strip().lower()
    if code.isdigit():
        code = f"bg{int(code)}"
    return code if code in BACKGROUNDS else None


def ensure_background_columns(connection):
    existing = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "active_bg" not in existing:
        connection.execute(f"ALTER TABLE users ADD COLUMN active_bg TEXT DEFAULT '{DEFAULT_BG}'")
    for code in BACKGROUNDS:
        if code not in existing:
            connection.execute(f"ALTER TABLE users ADD COLUMN {code} INTEGER DEFAULT 0")
    if "active_border" not in existing:
        connection.execute("ALTER TABLE users ADD COLUMN active_border TEXT DEFAULT 'default'")
    for code in AVATAR_BORDERS:
        if code not in existing:
            connection.execute(f"ALTER TABLE users ADD COLUMN {code} INTEGER DEFAULT 0")


def get_shop_state(user_id):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            columns = ", ".join(BACKGROUNDS)
            row = connection.execute(
                f"SELECT balance, active_bg, {columns} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    balance, active = row[0], row[1]
    owned = {code for code, flag in zip(BACKGROUNDS, row[2:]) if flag}
    owned.add(DEFAULT_BG)
    if user_id == DEV_USER_ID:
        owned = set(BACKGROUNDS.keys())
    if active not in BACKGROUNDS:
        active = DEFAULT_BG
    return balance, owned, active


def unlock_specific_background(user_id, bg_code):
    with closing(sqlite3.connect("database.db")) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            connection.execute(f"UPDATE users SET {bg_code} = 1, active_bg = ? WHERE user_id = ?", (bg_code, user_id))
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise


def buy_background(user_id, bg_code, payment_method="coins"):
    """Buy a background with either 4,000,000 coins or 30 AAA items."""
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"

    item = BACKGROUNDS[bg_code]
    if user_id == DEV_USER_ID:
        return True, f"Developer privilege: {item['name']} is already yours!"
    if bg_code == DEFAULT_BG:
        return False, f"{item['name']} is free by default."
    if payment_method not in ("coins", "aaa"):
        return False, "Choose either coins or AAA items to pay."

    with closing(sqlite3.connect("database.db", timeout=10)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            balance, aaa_count, owned = connection.execute(
                f"SELECT balance, aa_item, {bg_code} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if owned:
                connection.rollback()
                return False, f"You already own {item['name']}!"
            if payment_method == "coins":
                if balance < BACKGROUND_COIN_PRICE:
                    connection.rollback()
                    return False, f"You need {MONEY_EMOJI} {BACKGROUND_COIN_PRICE:,} to buy this background."
                connection.execute(
                    f"UPDATE users SET balance = balance - ?, {bg_code} = 1, active_bg = ? WHERE user_id = ?",
                    (BACKGROUND_COIN_PRICE, bg_code, user_id),
                )
                payment_text = f"{MONEY_EMOJI} {BACKGROUND_COIN_PRICE:,} coins"
            else:
                if aaa_count < BACKGROUND_AAA_PRICE:
                    connection.rollback()
                    return False, f"You need {BACKGROUND_AAA_PRICE} AAA to buy this background."
                connection.execute(
                    f"UPDATE users SET aa_item = aa_item - ?, {bg_code} = 1, active_bg = ? WHERE user_id = ?",
                    (BACKGROUND_AAA_PRICE, bg_code, user_id),
                )
                payment_text = f"{BACKGROUND_AAA_PRICE} AAA"
            connection.commit()
            return True, f"Purchased and equipped {item['name']} using {payment_text}!"
        except Exception:
            connection.rollback()
            raise


def equip_background(user_id, bg_code):
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"

    with closing(sqlite3.connect("database.db")) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            if user_id != DEV_USER_ID and bg_code != DEFAULT_BG:
                owned = connection.execute(
                    f"SELECT {bg_code} FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
                if not owned:
                    connection.rollback()
                    return False, "You do not own this background!"

            connection.execute("UPDATE users SET active_bg = ? WHERE user_id = ?", (bg_code, user_id))
            connection.commit()
            return True, f"Successfully equipped {BACKGROUNDS[bg_code]['name']}!"
        except Exception:
            connection.rollback()
            raise



def get_border_state(user_id):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            columns = ", ".join(AVATAR_BORDERS)
            row = connection.execute(
                f"SELECT aa_item, balance, active_border, {columns} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
    aaa_count, balance, active = row[:3]
    owned = {code for code, flag in zip(AVATAR_BORDERS, row[3:]) if flag}
    if user_id == DEV_USER_ID:
        owned = set(AVATAR_BORDERS)
    if active not in (DEFAULT_BORDER, *AVATAR_BORDERS):
        active = DEFAULT_BORDER
    return aaa_count, balance, active, owned


def buy_avatar_border(user_id, border_code, payment_method="coins"):
    if border_code not in AVATAR_BORDERS:
        return False, "Avatar border not found."
    if payment_method not in ("coins", "aaa"):
        return False, "Choose either coins or AAA items to pay."
    if user_id == DEV_USER_ID:
        return True, f"Developer privilege: {AVATAR_BORDERS[border_code]['name']} is already yours!"
    coin_price, aaa_price = border_prices(border_code)
    with closing(sqlite3.connect("database.db", timeout=10)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            balance, aaa_count, owned = connection.execute(
                f"SELECT balance, aa_item, {border_code} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if owned:
                connection.rollback()
                return False, "You already own this avatar border. Equip it from the shop."
            if payment_method == "coins":
                if balance < coin_price:
                    connection.rollback()
                    return False, f"You need {MONEY_EMOJI} {coin_price:,} coins."
                connection.execute(
                    f"UPDATE users SET balance = balance - ?, {border_code} = 1, active_border = ? WHERE user_id = ?",
                    (coin_price, border_code, user_id),
                )
                paid = f"{MONEY_EMOJI} {coin_price:,} coins"
            else:
                if aaa_count < aaa_price:
                    connection.rollback()
                    return False, f"You need {aaa_price} AAA."
                connection.execute(
                    f"UPDATE users SET aa_item = aa_item - ?, {border_code} = 1, active_border = ? WHERE user_id = ?",
                    (aaa_price, border_code, user_id),
                )
                paid = f"{aaa_price} AAA"
            connection.commit()
            return True, f"Purchased and equipped {AVATAR_BORDERS[border_code]['name']} using {paid}!"
        except Exception:
            connection.rollback()
            raise


def equip_avatar_border(user_id, border_code):
    if border_code == DEFAULT_BORDER:
        with closing(sqlite3.connect("database.db")) as connection:
            with connection:
                connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                ensure_background_columns(connection)
                connection.execute("UPDATE users SET active_border = ? WHERE user_id = ?", (DEFAULT_BORDER, user_id))
        return True, "Default avatar border equipped."
    if border_code not in AVATAR_BORDERS:
        return False, "Avatar border not found."
    with closing(sqlite3.connect("database.db")) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            owned = connection.execute(f"SELECT {border_code} FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
            if not owned and user_id != DEV_USER_ID:
                connection.rollback()
                return False, "You do not own this avatar border yet."
            connection.execute("UPDATE users SET active_border = ? WHERE user_id = ?", (border_code, user_id))
            connection.commit()
            return True, f"Equipped {AVATAR_BORDERS[border_code]['name']}!"
        except Exception:
            connection.rollback()
            raise


def get_user_avatar_border(user_id):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            row = connection.execute("SELECT active_border FROM users WHERE user_id = ?", (user_id,)).fetchone()
    code = row[0] if row and row[0] in AVATAR_BORDERS else DEFAULT_BORDER
    return code

def sell_background(user_id, bg_code):
    bg_code = normalize_bg_code(bg_code)
    if bg_code is None:
        return False, "Background not found!"
    if user_id == DEV_USER_ID:
        return False, "Developer cannot sell backgrounds!"
    if bg_code == DEFAULT_BG:
        return False, "Cannot sell default background!"

    item = BACKGROUNDS[bg_code]
    sell_price = 500_000

    with closing(sqlite3.connect("database.db")) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)

            row = connection.execute(
                f"SELECT balance, active_bg, {bg_code} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            balance, active_bg, owned = row[0], row[1], row[2]

            if not owned:
                connection.rollback()
                return False, f"You do not own {item['name']}!"
            if active_bg == bg_code:
                connection.rollback()
                return False, "Cannot sell currently equipped background!"

            new_balance = balance + sell_price
            connection.execute(
                f"UPDATE users SET balance = ?, {bg_code} = 0 WHERE user_id = ?",
                (new_balance, user_id),
            )
            connection.commit()
            return True, f"Sold {item['name']} for {MONEY_EMOJI} {sell_price:,}!"
        except Exception:
            connection.rollback()
            raise


def get_user_background_filename(user_id):
    with closing(sqlite3.connect("database.db")) as connection:
        with connection:
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            ensure_background_columns(connection)
            row = connection.execute("SELECT active_bg FROM users WHERE user_id = ?", (user_id,)).fetchone()
    code = row[0] if row and row[0] in BACKGROUNDS else DEFAULT_BG
    return BACKGROUNDS[code]["filename"]


def check_background_files():
    missing = [
        info["filename"] for info in BACKGROUNDS.values()
        if not os.path.isfile(os.path.join(_BG_DIR, info["filename"]))
    ]
    if missing:
        print(f"[warning] missing background images in '{_BG_DIR}': {', '.join(missing)}")
    else:
        print(f"All {len(BACKGROUNDS)} background images found.")


# ---------------------------------------------------------------------------
# 🛍️ MOBILE-FRIENDLY SHOP  (ashop / ash)
#   Main menu  : wallet + two dropdowns, nothing else.
#   Preview    : opens in the same message when an item is picked.
# ---------------------------------------------------------------------------
SHOP_COLOR = discord.Color.from_rgb(147, 112, 219)

# One table drives both item types so the UI code is written only once.
SHOP_KINDS = {
    "bg": {
        "catalog": BACKGROUNDS,
        "default": DEFAULT_BG,
        "icon": "🖼️",
        "footer": "Backgrounds",
    },
    "border": {
        "catalog": AVATAR_BORDERS,
        "default": DEFAULT_BORDER,
        "icon": "✨",
        "footer": "Avatar Borders & Glow",
    },
}


def _price_line(kind, code):
    """Exact price text, e.g. '4,000,000 Coins or 30 AAA'. Free default item shows 'Free'."""
    if kind == "bg":
        if code == DEFAULT_BG:
            return "**Free**"
        return f"**{BACKGROUND_COIN_PRICE:,} Coins** or **{BACKGROUND_AAA_PRICE} AAA**"
    coins, aaa = border_prices(code)
    return f"**{coins:,} Coins** or **{aaa} AAA**"


def _item_state(user_id, kind, code):
    """Return what the user can currently do with an item."""
    if kind == "bg":
        _bal, owned, active = get_shop_state(user_id)
        default_code = DEFAULT_BG
    else:
        _aaa, _bal, active, owned = get_border_state(user_id)
        default_code = DEFAULT_BORDER
    is_owned = code in owned or code == default_code
    is_equipped = code == active
    if is_equipped:
        label = "🟢 Equipped"
    elif is_owned:
        label = "🟣 Owned"
    else:
        label = "⚪ Available"
    return {
        "owned": is_owned,
        "equipped": is_equipped,
        "default_active": active == default_code,
        "label": label,
    }


def _wallet(user_id):
    data = get_user_data(user_id)
    return data[0], data[6]  # (coins, AAA)


def _shop_result_embed(success, msg):
    return discord.Embed(
        title="✅ Done" if success else "❌ Couldn't complete that",
        description=msg,
        color=discord.Color.green() if success else discord.Color.red(),
    )


# ----------------------------- Main menu -----------------------------------
def _dropdown_options(user_id, kind):
    """Dropdown rows show only the name + status. Prices live in the preview panel."""
    catalog = SHOP_KINDS[kind]["catalog"]
    if kind == "bg":
        _bal, owned, active = get_shop_state(user_id)
    else:
        _aaa, _bal, active, owned = get_border_state(user_id)
    options = []
    for code, info in catalog.items():
        if code == active:
            status = "Equipped"
        elif code in owned or code == SHOP_KINDS[kind]["default"]:
            status = "Owned"
        else:
            status = "Available"
        options.append(discord.SelectOption(label=info["name"][:100], value=code, description=status))
    return options


class ShopDropdown(discord.ui.Select):
    def __init__(self, user_id, kind):
        self.user_id = user_id
        self.kind = kind
        placeholder = "🖼️ Choose a Background" if kind == "bg" else "✨ Choose a Border & Glow"
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=_dropdown_options(user_id, kind),
            row=0 if kind == "bg" else 1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This shop session is not yours.", ephemeral=True)
        await interaction.response.defer()  # rendering the preview image can take > 3s
        await _show_panel(interaction, self.kind, self.values[0])


class MainShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.add_item(ShopDropdown(user_id, "bg"))
        self.add_item(ShopDropdown(user_id, "border"))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ, row=2))


def create_main_shop_embed(user_id):
    coins, aaa = _wallet(user_id)
    embed = discord.Embed(
        title="🛍️ Profile Shop",
        description=f"🔷 **{coins:,}** Coins\n💎 **{aaa:,}** AAA\n\nPick an item below to preview it.",
        color=SHOP_COLOR,
    )
    embed.set_footer(text="See your result with aup / ap")
    return embed, MainShopView(user_id)


# ---------------------------- Preview panel --------------------------------
async def _create_shop_preview(user, guild, bg_code=None, border_code=None):
    """Render the exact profile card being previewed. Returns (path, discord.File)."""
    user_id = user.id
    _balance, _bank, _xp, level, chat_xp, voice_xp, aaa_count = get_user_data(user_id)
    bg_filename = BACKGROUNDS[bg_code]["filename"] if bg_code else get_user_background_filename(user_id)
    ring_style = border_code if border_code else get_user_avatar_border(user_id)

    avatar_bytes = await user.display_avatar.with_size(512).read()
    server_icon_bytes = None
    if guild and guild.icon:
        try:
            server_icon_bytes = await guild.icon.with_size(128).read()
        except discord.DiscordException:
            pass

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"shop_preview_{user_id}_{random.randrange(1, 1_000_000_000)}.png",
    )
    await asyncio.to_thread(
        generate_profile_card,
        avatar_bytes,
        user.display_name,
        level,
        chat_xp,
        voice_xp,
        aaa_count,
        guild.name if guild else "Server",
        server_icon_bytes,
        output_path,
        bg_filename,
        ring_style,
    )
    return output_path, discord.File(output_path, filename="profile-preview.png")


def _panel_embed(user_id, kind, code, notice=None):
    info = SHOP_KINDS[kind]["catalog"][code]
    state = _item_state(user_id, kind, code)
    coins, aaa = _wallet(user_id)

    lines = []
    if notice:
        lines.append(notice)
        lines.append("")
    lines.append(f"**Status:** {state['label']}")
    lines.append(f"**Price:** {_price_line(kind, code)}")

    if kind == "border":
        color = discord.Color.from_rgb(*info["start"][:3])
    else:
        color = SHOP_COLOR
    embed = discord.Embed(title=info["name"], description="\n".join(lines), color=color)
    embed.set_image(url="attachment://profile-preview.png")
    embed.set_footer(text=f"🔷 {coins:,}  •  💎 {aaa:,}")
    return embed


class ItemPanelView(discord.ui.View):
    """Buy / Equip / Default / Back. Buttons that don't apply are greyed out."""

    def __init__(self, user_id, kind, code):
        super().__init__(timeout=300)
        self.user_id, self.kind, self.code = user_id, kind, code
        state = _item_state(user_id, kind, code)
        self.buy_button.disabled = state["owned"]
        self.equip_button.disabled = (not state["owned"]) or state["equipped"]
        self.default_button.disabled = state["default_active"]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Buy", emoji="🛒", style=discord.ButtonStyle.success, row=0)
    async def buy_button(self, interaction: discord.Interaction, _button):
        name = SHOP_KINDS[self.kind]["catalog"][self.code]["name"]
        await interaction.response.send_message(
            content=f"Pay for **{name}** with:",
            view=PaymentView(self.user_id, self.kind, self.code, interaction.message),
            ephemeral=True,
        )

    @discord.ui.button(label="Equip", emoji="✨", style=discord.ButtonStyle.primary, row=0)
    async def equip_button(self, interaction: discord.Interaction, _button):
        await interaction.response.defer()
        if self.kind == "bg":
            ok, msg = equip_background(self.user_id, self.code)
        else:
            ok, msg = equip_avatar_border(self.user_id, self.code)
        await _show_panel(interaction, self.kind, self.code, notice=("✅ " if ok else "❌ ") + msg)

    @discord.ui.button(label="Default", emoji="↩️", style=discord.ButtonStyle.secondary, row=0)
    async def default_button(self, interaction: discord.Interaction, _button):
        await interaction.response.defer()
        if self.kind == "bg":
            ok, msg = equip_background(self.user_id, DEFAULT_BG)
        else:
            ok, msg = equip_avatar_border(self.user_id, DEFAULT_BORDER)
        await _show_panel(interaction, self.kind, self.code, notice=("✅ " if ok else "❌ ") + msg)

    @discord.ui.button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
    async def back_button(self, interaction: discord.Interaction, _button):
        embed, view = create_main_shop_embed(self.user_id)
        await interaction.response.edit_message(embed=embed, view=view, attachments=[])


def _discard_preview(file, path):
    try:
        file.close()
    except Exception:
        pass
    try:
        os.remove(path)
    except OSError:
        pass


async def _show_panel(interaction, kind, code, notice=None):
    """Render the preview panel into the message this (already deferred) interaction came from."""
    try:
        param = {"bg_code": code} if kind == "bg" else {"border_code": code}
        path, file = await _create_shop_preview(interaction.user, interaction.guild, **param)
    except Exception:
        traceback.print_exc()
        return await interaction.followup.send("Sorry, the preview could not be generated.", ephemeral=True)
    try:
        await interaction.edit_original_response(
            embed=_panel_embed(interaction.user.id, kind, code, notice),
            view=ItemPanelView(interaction.user.id, kind, code),
            attachments=[file],
        )
    finally:
        _discard_preview(file, path)


# ------------------------------- Payment -----------------------------------
class PaymentView(discord.ui.View):
    """Ephemeral two-button picker: Coins or AAA."""

    def __init__(self, user_id, kind, code, parent_message):
        super().__init__(timeout=120)
        self.user_id, self.kind, self.code = user_id, kind, code
        self.parent_message = parent_message
        if kind == "bg":
            coin_price, aaa_price = BACKGROUND_COIN_PRICE, BACKGROUND_AAA_PRICE
        else:
            coin_price, aaa_price = border_prices(code)
        self.coins_button.label = f"{coin_price:,} Coins"
        self.aaa_button.label = f"{aaa_price} AAA"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This purchase menu is not yours.", ephemeral=True)
            return False
        return True

    async def _purchase(self, interaction, method):
        if self.kind == "bg":
            ok, msg = buy_background(self.user_id, self.code, method)
        else:
            ok, msg = buy_avatar_border(self.user_id, self.code, method)
        # Answer immediately (3s limit), then refresh the public panel.
        await interaction.response.edit_message(content=None, embed=_shop_result_embed(ok, msg), view=None)
        if ok and self.parent_message is not None:
            try:
                param = {"bg_code": self.code} if self.kind == "bg" else {"border_code": self.code}
                path, file = await _create_shop_preview(interaction.user, interaction.guild, **param)
                try:
                    await self.parent_message.edit(
                        embed=_panel_embed(self.user_id, self.kind, self.code, "✅ Purchased and equipped!"),
                        view=ItemPanelView(self.user_id, self.kind, self.code),
                        attachments=[file],
                    )
                finally:
                    _discard_preview(file, path)
            except (discord.HTTPException, OSError):
                traceback.print_exc()

    @discord.ui.button(label="Coins", emoji="🔷", style=discord.ButtonStyle.success)
    async def coins_button(self, interaction: discord.Interaction, _button):
        await self._purchase(interaction, "coins")

    @discord.ui.button(label="AAA", emoji="💎", style=discord.ButtonStyle.primary)
    async def aaa_button(self, interaction: discord.Interaction, _button):
        await self._purchase(interaction, "aaa")


def format_hours_minutes(remaining):
    total_minutes = math.ceil(remaining.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def format_days_hours(remaining):
    total_hours = math.ceil(remaining.total_seconds() / 3600)
    days, hours = divmod(total_hours, 24)
    return f"{days}d {hours}h"


def format_k(value):
    for limit, suffix in ((1_000_000, "M"), (1_000, "K")):
        if value >= limit:
            val = value / limit
            return f"{int(val)}{suffix}" if val.is_integer() else f"{val:.1f}{suffix}"
    return str(value)


SCALE = 2

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_BG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background")

_BOLD_FONTS = [
    "Poppins-Bold.ttf", "Inter-Bold.ttf", "Montserrat-Bold.ttf", "segoeuib.ttf", "arialbd.ttf",
    "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
_REGULAR_FONTS = [
    "Poppins-Medium.ttf", "Inter-Regular.ttf", "Montserrat-Medium.ttf", "segoeui.ttf", "arial.ttf",
    "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_font_cache = {}


def load_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    px = int(size * SCALE)
    font = None
    for name in (_BOLD_FONTS if bold else _REGULAR_FONTS):
        for candidate in (os.path.join(_FONT_DIR, name), name):
            try:
                font = ImageFont.truetype(candidate, px)
                break
            except OSError:
                continue
        if font:
            break
    if font is None:
        font = ImageFont.load_default(px)

    _font_cache[key] = font
    return font


def sanitize_username(username):
    normalized = unicodedata.normalize("NFKD", username)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9 _.-]", "", ascii_name)
    safe_name = " ".join(safe_name.split()).strip()
    return safe_name or "Player"


def sanitize_servername(server_name):
    normalized = unicodedata.normalize("NFKD", server_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9 _.-]", "", ascii_name)
    safe_name = " ".join(safe_name.split()).strip()
    return safe_name or "Server"


def _s(value):
    return int(round(value * SCALE))


def _fit_text(draw, text, max_width, start_size, min_size, bold=True):
    size = start_size
    while size >= min_size:
        font = load_font(size, bold)
        if draw.textlength(text, font=font) <= _s(max_width):
            return font, text
        size -= 2
    font = load_font(min_size, bold)
    while len(text) > 1 and draw.textlength(text + "...", font=font) > _s(max_width):
        text = text[:-1]
    return font, text.rstrip() + "..."


def _diagonal_gradient(size, c1, c2):
    w, h = size
    base = Image.linear_gradient("L")
    vertical = base.resize((w, h), Image.Resampling.BILINEAR)
    horizontal = base.rotate(90).resize((w, h), Image.Resampling.BILINEAR)
    mask = Image.blend(vertical, horizontal, 0.5)
    return Image.composite(Image.new("RGBA", (w, h), c2), Image.new("RGBA", (w, h), c1), mask)


def _horizontal_gradient(size, c1, c2):
    w, h = size
    mask = Image.linear_gradient("L").rotate(90).resize((w, h), Image.Resampling.BILINEAR)
    return Image.composite(Image.new("RGBA", (w, h), c2), Image.new("RGBA", (w, h), c1), mask)


def _blend_rounded_rect(card, box, radius, fill, outline=None, width=0):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    layer = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (0, 0, x1 - x0, y1 - y0), radius=radius, fill=fill, outline=outline, width=width,
    )
    card.alpha_composite(layer, (x0, y0))


def _draw_progress_bar(card, x0, y0, x1, y1, ratio, c1, c2):
    height = y1 - y0
    width = x1 - x0
    _blend_rounded_rect(card, (x0, y0, x1, y1), height // 2, (255, 255, 255, 26))

    ratio = max(0.0, min(1.0, ratio))
    if ratio <= 0:
        return
    fill_w = max(height, int(width * ratio))

    strip = _horizontal_gradient((fill_w, height), c1, c2)
    gloss = Image.new("RGBA", (fill_w, height), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rectangle((0, 0, fill_w, height // 2), fill=(255, 255, 255, 38))
    strip = Image.alpha_composite(strip, gloss)

    mask = Image.new("L", (fill_w, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fill_w - 1, height - 1), radius=height // 2, fill=255)
    card.paste(strip, (x0, y0), mask)


def _mix(c1, c2, t):
    """Blend colour c1 toward c2 by t (0..1). Always returns an opaque RGBA tuple."""
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (255,)


def _profile_theme(ring_style):
    """Every colour on the profile card is derived from the equipped border."""
    info = AVATAR_BORDERS.get(ring_style)
    if info:
        a, b, glow = info["start"], info["end"], info["glow"]
    else:  # default border: understated silver
        a, b, glow = (190, 200, 220, 255), (115, 130, 160, 255), (170, 180, 205, 90)
    dark = (14, 8, 30, 255)
    return {
        "start": a,
        "end": b,
        "glow": glow,
        "tint": (*b[:3], 46),                              # colour wash over the background
        "panel_fill": (*_mix(dark, b, 0.16)[:3], 168),     # stat boxes
        "panel_outline": (*a[:3], 85),
        "muted": _mix(a, (255, 255, 255, 255), 0.62),      # small secondary text
        "gap_fill": _mix(dark, b, 0.10),                   # dark gap between avatar and ring
    }


def _draw_stat_box(card, draw, box, label, level, current, maximum, total_xp, c1, c2, theme=None):
    x0, y0, x1, y1 = box
    pad = _s(32)
    fill = theme["panel_fill"] if theme else (20, 10, 40, 160)
    outline = theme["panel_outline"] if theme else (200, 150, 255, 40)
    muted = theme["muted"] if theme else (210, 180, 240, 255)

    _blend_rounded_rect(card, box, _s(28), fill, outline=outline, width=_s(1))

    row1 = y0 + _s(42)
    label_font = load_font(28, bold=True)
    draw.text((x0 + pad, row1), label, font=label_font, fill=c2, anchor="lm")
    label_w = draw.textlength(label + " ", font=label_font)
    draw.text((x0 + pad + label_w, row1), f"LV {level}", font=label_font, fill=(255, 255, 255, 255), anchor="lm")

    xp_unit_font = load_font(16, bold=False)
    xp_font = load_font(30, bold=True)
    right = x1 - pad
    draw.text((right, row1 + _s(3)), "XP", font=xp_unit_font, fill=muted, anchor="rm")
    unit_w = draw.textlength("XP", font=xp_unit_font)
    draw.text((right - unit_w - _s(8), row1), format_k(total_xp), font=xp_font, fill=(255, 255, 255, 255), anchor="rm")

    text_y = y0 + _s(86)
    small = load_font(16, bold=False)
    draw.text((x0 + pad, text_y), f"{current} / {maximum} XP", font=small, fill=muted, anchor="ls")
    pct = int(min(current / maximum, 1.0) * 100) if maximum else 0
    draw.text((x1 - pad, text_y), f"{pct}%", font=small, fill=muted, anchor="rs")

    _draw_progress_bar(
        card, x0 + pad, y0 + _s(98), x1 - pad, y0 + _s(122),
        (current / maximum) if maximum else 0, c1, c2,
    )


# ---------------------------------------------------------------------------
# Avatar ring styles. Each one has a different SHAPE, not just a different colour:
#   double  - thick ring + thin floating outer ring        (Aurora Pulse)
#   rays    - ring with a crown of sun rays                (Solar Flare)
#   dashed  - segmented ring + faint outer halo ring       (Emerald Mist)
#   orbs    - slim ring with orbiting beads                (Sakura Dream)
#   royal   - heavy ring with diamond ornaments            (Royal Gold)
# ---------------------------------------------------------------------------
def _polar(cx, cy, radius, degrees):
    a = math.radians(degrees)
    return cx + radius * math.cos(a), cy + radius * math.sin(a)


def _paste_gradient(card, cx, cy, size, mask, c1, c2):
    gradient = _diagonal_gradient((size, size), c1, c2)
    card.paste(gradient, (cx - size // 2, cy - size // 2), mask)


def _draw_avatar_ring(card, cx, cy, inner_r, thickness, ring_style):
    """Draw the ring on `card` (in place). `inner_r` is the radius where the ring starts."""
    info = AVATAR_BORDERS.get(ring_style)
    if info and info.get("shape") in PREMIUM_SHAPES:
        draw_premium_ring(card, cx, cy, inner_r, thickness, info["shape"])
        return
    outer_r = inner_r + thickness
    size = (outer_r + _s(30)) * 2          # canvas big enough for ornaments
    mid = size // 2

    def new_mask():
        m = Image.new("L", (size, size), 0)
        return m, ImageDraw.Draw(m)

    def annulus(d, r_in, r_out, value=255):
        d.ellipse((mid - r_out, mid - r_out, mid + r_out, mid + r_out), fill=value)
        d.ellipse((mid - r_in, mid - r_in, mid + r_in, mid + r_in), fill=0)

    if not info:  # default: simple neutral ring
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, (190, 200, 220, 255), (95, 105, 130, 255))
        return

    c1, c2, shape = info["start"], info["end"], info["shape"]

    if shape == "double":
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        m2, d2 = new_mask()
        annulus(d2, outer_r + _s(5), outer_r + _s(8))
        _paste_gradient(card, cx, cy, size, m2, c2, c1)

    elif shape == "rays":
        m, d = new_mask()
        annulus(d, inner_r, outer_r)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        rays, rd = new_mask()
        count = 36
        for i in range(count):
            ang = i * 360 / count
            length = _s(17) if i % 2 == 0 else _s(9)
            half = 2.6 if i % 2 == 0 else 2.0
            base = outer_r + _s(2)
            pts = [_polar(mid, mid, base, ang - half), _polar(mid, mid, base + length, ang),
                   _polar(mid, mid, base, ang + half)]
            rd.polygon(pts, fill=255)
        _paste_gradient(card, cx, cy, size, rays, c2, c1)

    elif shape == "dashed":
        m, d = new_mask()
        segments = 18
        for i in range(segments):
            start = i * (360 / segments) + 2
            d.pieslice((mid - outer_r - _s(2), mid - outer_r - _s(2), mid + outer_r + _s(2), mid + outer_r + _s(2)),
                       start, start + (360 / segments) - 6, fill=255)
        d.ellipse((mid - inner_r, mid - inner_r, mid + inner_r, mid + inner_r), fill=0)
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        halo, hd = new_mask()
        annulus(hd, outer_r + _s(10), outer_r + _s(12), value=130)
        _paste_gradient(card, cx, cy, size, halo, c2, c1)

    elif shape == "orbs":
        m, d = new_mask()
        annulus(d, inner_r, inner_r + max(_s(4), thickness // 2))
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        orb_orbit = outer_r + _s(10)
        big, bd = new_mask()
        small, sd = new_mask()
        for i in range(12):
            ang = i * 30
            x, y = _polar(mid, mid, orb_orbit, ang)
            r = _s(7) if i % 2 == 0 else _s(4)
            target = bd if i % 2 == 0 else sd
            target.ellipse((x - r, y - r, x + r, y + r), fill=255)
        _paste_gradient(card, cx, cy, size, big, c1, c2)
        _paste_gradient(card, cx, cy, size, small, c2, c1)

    elif shape == "royal":
        m, d = new_mask()
        annulus(d, inner_r, outer_r + _s(2))
        _paste_gradient(card, cx, cy, size, m, c1, c2)
        thin, td = new_mask()
        annulus(td, outer_r + _s(6), outer_r + _s(8))
        _paste_gradient(card, cx, cy, size, thin, c2, c1)
        gems, gd = new_mask()
        for ang in (0, 90, 180, 270):          # large diamonds
            pts = [_polar(mid, mid, outer_r + _s(2), ang),
                   _polar(mid, mid, outer_r + _s(12), ang - 11),
                   _polar(mid, mid, outer_r + _s(22), ang),
                   _polar(mid, mid, outer_r + _s(12), ang + 11)]
            gd.polygon(pts, fill=255)
        for ang in (45, 135, 225, 315):        # small diamonds
            pts = [_polar(mid, mid, outer_r + _s(5), ang),
                   _polar(mid, mid, outer_r + _s(11), ang - 7),
                   _polar(mid, mid, outer_r + _s(17), ang),
                   _polar(mid, mid, outer_r + _s(11), ang + 7)]
            gd.polygon(pts, fill=255)
        _paste_gradient(card, cx, cy, size, gems, (255, 245, 190, 255), c2)


def generate_profile_card(
    avatar_bytes, username, level, chat_xp, voice_xp, aaa_count,
    server_name="Server", server_icon_bytes=None, output_path="profile_card.png", bg_filename="bdg1.png", ring_style=DEFAULT_BORDER,
):
    W, H = 1200, 480
    w, h = _s(W), _s(H)
    username = sanitize_username(username)
    server_name = sanitize_servername(server_name)
    theme = _profile_theme(ring_style)
    accent_start, accent_end = theme["start"], theme["end"]

    bg_path = os.path.join(_BG_DIR, bg_filename)
    try:
        bg = Image.open(bg_path).convert("RGBA")
        bg = ImageOps.fit(bg, (w, h), method=Image.Resampling.LANCZOS)
        bg = Image.alpha_composite(Image.new("RGBA", (w, h), (25, 12, 45, 255)), bg)
        bg = Image.alpha_composite(bg, Image.new("RGBA", (w, h), (20, 10, 35, 100)))
    except Exception as exc:
        print(f"[profile card] could not load background '{bg_path}': {exc}")
        bg = _diagonal_gradient((w, h), (90, 40, 140, 255), (25, 12, 45, 255))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((_s(760), _s(-190), _s(1290), _s(170)), fill=(220, 90, 210, 90))
        glow_draw.ellipse((_s(-150), _s(280), _s(380), _s(650)), fill=(120, 80, 255, 90))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(_s(70))))
    # Theme wash: the equipped border tints the whole card, not just the ring.
    bg = Image.alpha_composite(bg, Image.new("RGBA", (w, h), theme["tint"]))

    corner_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=_s(36), fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(bg, (0, 0), corner_mask)
    _blend_rounded_rect(
        card, (_s(1), _s(1), w - _s(1) - 1, h - _s(1) - 1),
        _s(36), None, outline=(*accent_start[:3], 145), width=_s(2),
    )
    draw = ImageDraw.Draw(card)

    right_edge = _s(1144)
    icon_size = _s(40)
    current_x = right_edge

    if server_icon_bytes:
        try:
            s_icon = Image.open(io.BytesIO(server_icon_bytes)).convert("RGBA")
            s_icon = ImageOps.fit(s_icon, (icon_size, icon_size), method=Image.Resampling.LANCZOS)
            s_mask = Image.new("L", (icon_size, icon_size), 0)
            ImageDraw.Draw(s_mask).ellipse((0, 0, icon_size - 1, icon_size - 1), fill=255)
            card.paste(s_icon, (right_edge - icon_size, _s(48)), s_mask)
            current_x = right_edge - icon_size - _s(14)
        except Exception:
            pass

    name_font, name_text = _fit_text(draw, server_name, 280, 20, 14, bold=False)
    draw.text((current_x, _s(68)), name_text, font=name_font, fill=(255, 255, 255, 255), anchor="rm")

    col_cx = _s(224)
    avatar_d = _s(190)
    ring = _s(8)
    gap = _s(4)
    center_y = _s(196)
    inner_r = avatar_d // 2 + gap
    outer_r = inner_r + ring

    # Glow: a tight halo hugging the ring plus a wide soft wash behind the avatar column.
    info = AVATAR_BORDERS.get(ring_style)
    blur = _s(info["glow_blur"]) if info else _s(22)
    spread = _s(info["glow_spread"]) if info else _s(14)
    glow2 = info.get("glow2") if info else None
    shift = _s(9) if glow2 else 0                      # two-tone glow: the 2nd colour peeks out the other side
    for color, dx, dy in ((glow2, shift, shift // 2), (theme["glow"], -shift, -shift // 2)):
        if color is None:
            continue
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse(
            (col_cx - outer_r - spread + dx, center_y - outer_r - spread + dy,
             col_cx + outer_r + spread + dx, center_y + outer_r + spread + dy), fill=color)
        card = Image.alpha_composite(card, halo.filter(ImageFilter.GaussianBlur(blur)))
    wash = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    wash_r = outer_r + _s(80)
    ImageDraw.Draw(wash).ellipse((col_cx - wash_r, center_y - wash_r, col_cx + wash_r, center_y + wash_r),
                                 fill=(*theme["glow"][:3], 38 if info else 14))
    card = Image.alpha_composite(card, wash.filter(ImageFilter.GaussianBlur(_s(55))))

    _draw_avatar_ring(card, col_cx, center_y, inner_r, ring, ring_style)

    draw = ImageDraw.Draw(card)
    draw.ellipse((col_cx - inner_r, center_y - inner_r, col_cx + inner_r, center_y + inner_r),
                 fill=theme["gap_fill"])

    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = ImageOps.fit(avatar, (avatar_d, avatar_d), method=Image.Resampling.LANCZOS)
    except Exception:
        avatar = Image.new("RGBA", (avatar_d, avatar_d), (80, 45, 120, 255))
    avatar_mask = Image.new("L", (avatar_d, avatar_d), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, avatar_d - 1, avatar_d - 1), fill=255)
    card.paste(avatar, (col_cx - avatar_d // 2, center_y - avatar_d // 2), avatar_mask)
    draw = ImageDraw.Draw(card)

    user_font, user_text = _fit_text(draw, username, 330, 44, 26, bold=True)
    draw.text((col_cx, _s(350)), user_text, font=user_font, fill=(255, 255, 255, 255), anchor="mm")

    level_text = f"LEVEL {level} | AAA: {aaa_count:,}"
    level_font, level_text = _fit_text(draw, level_text, 290, 21, 14, bold=True)
    text_w = draw.textlength(level_text, font=level_font)
    pill_w, pill_h = text_w + _s(40), _s(38)
    pill_cy = _s(400)
    _blend_rounded_rect(
        card, (col_cx - pill_w / 2, pill_cy - pill_h / 2, col_cx + pill_w / 2, pill_cy + pill_h / 2),
        int(pill_h // 2), (*accent_start[:3], 70), outline=(*accent_end[:3], 180), width=_s(1),
    )
    draw.text((col_cx, pill_cy), level_text, font=level_font, fill=accent_start, anchor="mm")

    chat_level = (chat_xp // 500) + 1
    voice_level = (voice_xp // 500) + 1

    _draw_stat_box(
        card, draw, (_s(432), _s(120), _s(1144), _s(270)),
        "TEXT", chat_level, chat_xp % 500, 500, chat_xp,
        accent_start, accent_end, theme,
    )
    _draw_stat_box(
        card, draw, (_s(432), _s(290), _s(1144), _s(440)),
        "VOICE", voice_level, voice_xp % 500, 500, voice_xp,
        accent_end, accent_start, theme,
    )

    card = card.resize((W, H), Image.Resampling.LANCZOS)
    card.save(output_path, "PNG", optimize=True)
    return output_path


def generate_welcome_card(avatar_bytes, member_name, server_name, output_path="welcome_card.png"):
    W, H = 1024, 500
    w, h = _s(W), _s(H)
    member_name = sanitize_username(member_name)
    server_name = sanitize_servername(server_name)

    bg_path = os.path.join(_BG_DIR, "hello.png")
    try:
        bg = Image.open(bg_path).convert("RGBA")
        bg = ImageOps.fit(bg, (w, h), method=Image.Resampling.LANCZOS)
    except Exception as exc:
        print(f"[welcome card] could not load 'hello.png': {exc}")
        bg = _diagonal_gradient((w, h), (200, 130, 220, 255), (100, 50, 120, 255))

    corner_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=_s(30), fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(bg, (0, 0), corner_mask)
    
    overlay = Image.new("RGBA", (w, h), (180, 120, 220, 70))
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    col_cx, center_y = w // 2, _s(170)
    avatar_d = _s(180)
    ring = _s(8)
    gap = _s(4)
    outer_r = avatar_d // 2 + gap + ring

    ring_img = _diagonal_gradient((outer_r * 2, outer_r * 2), (255, 120, 200, 255), (220, 180, 255, 255))
    ring_mask = Image.new("L", (outer_r * 2, outer_r * 2), 0)
    ImageDraw.Draw(ring_mask).ellipse((0, 0, outer_r * 2 - 1, outer_r * 2 - 1), fill=255)
    card.paste(ring_img, (col_cx - outer_r, center_y - outer_r), ring_mask)

    gap_r = avatar_d // 2 + gap
    draw.ellipse((col_cx - gap_r, center_y - gap_r, col_cx + gap_r, center_y + gap_r), fill=(45, 20, 55, 255))

    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = ImageOps.fit(avatar, (avatar_d, avatar_d), method=Image.Resampling.LANCZOS)
    except Exception:
        avatar = Image.new("RGBA", (avatar_d, avatar_d), (130, 60, 110, 255))
    
    avatar_mask = Image.new("L", (avatar_d, avatar_d), 0)
    ImageDraw.Draw(avatar_mask).ellipse((0, 0, avatar_d - 1, avatar_d - 1), fill=255)
    card.paste(avatar, (col_cx - avatar_d // 2, center_y - avatar_d // 2), avatar_mask)
    draw = ImageDraw.Draw(card)

    welcome_font = load_font(40, bold=True)
    draw.text((col_cx, _s(310)), "✨ WELCOME PREMIUM ✨", font=welcome_font, fill=(255, 255, 255, 255), anchor="mm")

    name_font, name_text = _fit_text(draw, member_name, 800, 32, 20, bold=True)
    draw.text((col_cx, _s(370)), name_text, font=name_font, fill=(240, 210, 255, 255), anchor="mm")

    server_font, server_text = _fit_text(draw, f"To {server_name}", 800, 24, 16, bold=False)
    draw.text((col_cx, _s(420)), server_text, font=server_font, fill=(220, 190, 240, 255), anchor="mm")

    card = card.resize((W, H), Image.Resampling.LANCZOS)
    card.save(output_path, "PNG", optimize=True)
    return output_path


@tasks.loop(minutes=1)
async def voice_xp_task():
    for guild in client.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                if member.voice and (member.voice.self_mute or member.voice.self_deaf):
                    continue
                add_voice_xp(member.id, 15)


@client.event
async def on_ready():
    setup_database()
    check_background_files()
    if not voice_xp_task.is_running():
        voice_xp_task.start()
    
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} Slash Command(s) successfully!")
    except Exception as e:
        print(f"❌ Failed to sync Slash Commands: {e}")

    try:
        custom_status = discord.CustomActivity(name="✨ AMA nh sad nis tver mix bat sad")
        await client.change_presence(activity=custom_status)
    except Exception:
        activity = discord.Game(name="✨ AMA nh sad nis tver mix bat sad")
        await client.change_presence(activity=activity)
        
    print(f"Bot {client.user.name} is online!")

    try:
        dev_user = await client.fetch_user(DEV_USER_ID)
        dm_channel = await dev_user.create_dm()
        async for msg in dm_channel.history(limit=20):
            if msg.author.id == client.user.id:
                try:
                    await msg.delete()
                except Exception:
                    pass
        
        embed, view = create_dev_startup_embed_and_view(client)
        await dev_user.send(embed=embed, view=view)
    except Exception as e:
        print(f"Failed startup DM cleanup or send: {e}")


def format_meme_embed(target_user):
    meme = random.choice(MEME_QUOTES)
    if meme["type"] == "khmer":
        description_text = f"### {target_user.mention}\n\n**{meme['text']}**"
    else:
        description_text = f"### {target_user.mention}\n\n**{meme['en']}**\n**{meme['kh']}**"
    return discord.Embed(description=description_text, color=discord.Color.from_rgb(147, 112, 219))


# ---------------------------------------------------------------------
# Plain-text Rob / Steal command:  aoy @user   or   aoyyg @user
# (text command only - there is intentionally NO slash command for this)
#
#   * 50% success -> steal 10-35% of the target's CASH
#   * 50% caught  -> pay 5-15% of your own CASH to the target
#   * Bank money is never read or modified, so it is 100% safe
#   * Cooldown 5-10 min (random), stored in the database so a restart can't reset it
# ---------------------------------------------------------------------
ROB_MIN_THIEF_CASH = 5_000
ROB_MIN_TARGET_CASH = 10_000
ROB_COOLDOWN_RANGE = (300, 600)  # seconds


def _ensure_rob_column(connection):
    existing = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "rob_until" not in existing:
        connection.execute("ALTER TABLE users ADD COLUMN rob_until REAL DEFAULT 0")


def perform_robbery(thief_id, target_id):
    """
    One atomic transaction: cooldown check, balance checks, roll, transfer, cooldown write.
    Only the `balance` (cash) column is ever changed - never `bank`.

    Returns a dict with a "kind" of: "cooldown", "error", "success" or "caught".
    """
    with closing(sqlite3.connect("database.db", timeout=10)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            _ensure_rob_column(connection)
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (thief_id,))
            connection.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target_id,))

            thief_cash, rob_until = connection.execute(
                "SELECT balance, COALESCE(rob_until, 0) FROM users WHERE user_id = ?", (thief_id,)
            ).fetchone()
            target_cash = connection.execute(
                "SELECT balance FROM users WHERE user_id = ?", (target_id,)
            ).fetchone()[0]

            now = time.time()
            if rob_until > now:
                connection.rollback()
                return {"kind": "cooldown", "remaining": int(rob_until - now + 0.999)}
            if thief_cash < ROB_MIN_THIEF_CASH:
                connection.rollback()
                return {"kind": "error", "message": f"You need at least {MONEY_EMOJI} {ROB_MIN_THIEF_CASH:,} cash on hand to rob someone."}
            if target_cash < ROB_MIN_TARGET_CASH:
                connection.rollback()
                return {"kind": "error", "message": f"That member needs at least {MONEY_EMOJI} {ROB_MIN_TARGET_CASH:,} cash on hand to be robbed. Their bank is safe."}

            new_cooldown = now + random.randint(*ROB_COOLDOWN_RANGE)

            if random.random() < 0.5:
                percent = random.randint(10, 35)
                amount = max(1, target_cash * percent // 100)
                connection.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, target_id))
                connection.execute(
                    "UPDATE users SET balance = balance + ?, rob_until = ? WHERE user_id = ?",
                    (amount, new_cooldown, thief_id),
                )
                connection.commit()
                return {"kind": "success", "amount": amount, "percent": percent, "thief_cash": thief_cash + amount}

            percent = random.randint(5, 15)
            fine = max(1, thief_cash * percent // 100)
            connection.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (fine, target_id))
            connection.execute(
                "UPDATE users SET balance = balance - ?, rob_until = ? WHERE user_id = ?",
                (fine, new_cooldown, thief_id),
            )
            connection.commit()
            return {"kind": "caught", "amount": fine, "percent": percent, "thief_cash": thief_cash - fine}
        except Exception:
            connection.rollback()
            raise


def _resolve_rob_target(message, args):
    """Prefer the mention written right after the command; fall back to the first mention."""
    if args:
        match = re.fullmatch(r"<@!?(\d+)>", args[0])
        if match:
            wanted = int(match.group(1))
            for user in message.mentions:
                if user.id == wanted:
                    return user
    return message.mentions[0] if message.mentions else None


async def _cmd_rob(message, args):
    if message.guild is None:
        return await message.channel.send("Robbery only works inside a server.")

    target = _resolve_rob_target(message, args)
    if target is None:
        return await message.channel.send("Usage: `aoy @user` or `aoyyg @user`")

    thief = message.author
    if target.id == thief.id:
        return await message.channel.send("You can't rob yourself.")
    if target.bot:
        return await message.channel.send("You can't rob a bot.")

    result = perform_robbery(thief.id, target.id)
    kind = result["kind"]

    if kind == "cooldown":
        minutes, seconds = divmod(result["remaining"], 60)
        return await message.channel.send(embed=discord.Embed(
            title="⏳ Lay low for a bit",
            description=f"You can rob again in **{minutes}m {seconds:02d}s**.",
            color=discord.Color.orange(),
        ))
    if kind == "error":
        return await message.channel.send(embed=discord.Embed(
            description=f"🚫 {result['message']}", color=discord.Color.red(),
        ))

    if kind == "success":
        embed = discord.Embed(
            title="💰 Robbery Successful!",
            description=(f"{thief.mention} stole **{MONEY_EMOJI} {result['amount']:,}** "
                         f"({result['percent']}%) from {target.mention}!"),
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title="🚨 Caught!",
            description=(f"{thief.mention} got caught and paid **{MONEY_EMOJI} {result['amount']:,}** "
                         f"({result['percent']}% of their cash) to {target.mention} as compensation."),
            color=discord.Color.red(),
        )
    embed.set_thumbnail(url=thief.display_avatar.url)
    embed.set_footer(text=f"Your cash: {result['thief_cash']:,}  •  Bank money can't be robbed")
    await message.channel.send(embed=embed)


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None and message.author.id != DEV_USER_ID:
        return

    now_ts = asyncio.get_running_loop().time()
    if message.author.id not in chat_cooldowns or now_ts - chat_cooldowns[message.author.id] > 30:
        chat_cooldowns[message.author.id] = now_ts
        add_chat_xp(message.author.id, random.randint(10, 25))

    user_text = message.content.strip().lower()
    parts = message.content.strip().split()
    command = parts[0].lower() if parts else ""
    args = parts[1:]

    if command in ("aoy", "aoyyg"):
        await _cmd_rob(message, args)
        return

    if user_text == "astop":
        if message.channel.id in active_spam_tasks:
            active_spam_tasks[message.channel.id].cancel()
            del active_spam_tasks[message.channel.id]
            await message.channel.send("🛑 Stopped mentioning successfully!")
        else:
            await message.channel.send("⚠️ No active mention task running in this channel.")
        return

    if command == "aps":
        if not message.mentions:
            await message.channel.send("⚠️ Please mention a user! Usage: `aps @user <count> <text>`")
            return
        
        target_user = message.mentions[0]
        count = 10
        if len(parts) >= 3 and parts[2].isdigit():
            count = min(int(parts[2]), 1000)
            text_parts = parts[3:]
        else:
            text_parts = parts[2:]
            
        spam_text = " ".join(text_parts).strip()
        
        if message.channel.id in active_spam_tasks:
            await message.channel.send("⚠️ A mention loop is already running in this channel. Use `astop` first.")
            return

        async def run_spam():
            try:
                for _ in range(count):
                    msg_content = f"{target_user.mention} {spam_text}".strip()
                    await message.channel.send(msg_content)
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            finally:
                if message.channel.id in active_spam_tasks:
                    del active_spam_tasks[message.channel.id]

        task = asyncio.create_task(run_spam())
        active_spam_tasks[message.channel.id] = task
        return

    if user_text == "hi":
        await message.channel.send(f"✨ Hello! How are you, {message.author.display_name}? How can I help you today? 💜")

    elif user_text == "abal":
        balance, bank, xp, level, chat_xp, voice_xp, aa_count = get_user_data(message.author.id)

        embed_description = (
            f"**Coins :** `{balance:,}` {MONEY_EMOJI}\n"
            f"**Bank :** `{bank:,}` 🏦\n"
            f"**AAA :** `{aa_count:,}` 💎\n"
            f"───────────────\n"
            f"✨ **Total Wealth:** `{balance + bank:,}` Coins"
        )

        embed = discord.Embed(
            title=f"🌸 • | {message.author.display_name}'s Balance",
            description=embed_description,
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
        view = BalDirectShopView()
        await message.channel.send(embed=embed, view=view)

    elif command == "ajol":
        if not args:
            return await message.channel.send("⚠️ Usage: `ajol <amount>` or `ajol all`", delete_after=5)
        
        amt_arg = args[0].lower()
        success, result_val, msg = deposit_to_bank(message.author.id, amt_arg)
        
        if success:
            embed = discord.Embed(
                title="🏦 Bank Deposit Successful",
                description=f"✅ Successfully deposited **{MONEY_EMOJI} {result_val:,}** into your bank account!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Deposit Failed",
                description=f"Reason: **{msg}**",
                color=discord.Color.red()
            )
        await message.channel.send(embed=embed)

    elif command == "ajenh":
        if not args:
            return await message.channel.send("⚠️ Usage: `ajenh <amount>` or `ajenh all`", delete_after=5)
        
        amt_arg = args[0].lower()
        success, result_val, msg = withdraw_from_bank(message.author.id, amt_arg)
        
        if success:
            embed = discord.Embed(
                title="🏧 Bank Withdrawal Successful",
                description=f"✅ Successfully withdrew **{MONEY_EMOJI} {result_val:,}** from your bank account!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Withdrawal Failed",
                description=f"Reason: **{msg}**",
                color=discord.Color.red()
            )
        await message.channel.send(embed=embed)

    elif user_text == "ad":
        success, result = claim_reward(message.author.id, "last_daily", DAILY_REWARD, DAILY_COOLDOWN)
        if success:
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed",
                description=f"You successfully claimed your daily reward of **{MONEY_EMOJI} {DAILY_REWARD:,}**!\n\nNew Cash Balance: **{MONEY_EMOJI} {result:,}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="⏳ Daily Cooldown",
                description=f"You have already claimed your daily reward!\n\nPlease wait **{format_hours_minutes(result)}** before claiming again.",
                color=discord.Color.gold(),
            )
        await message.channel.send(embed=embed, view=StandardLinksView())

    elif user_text == "aw":
        success, result = claim_reward(message.author.id, "last_weekly", WEEKLY_REWARD, WEEKLY_COOLDOWN)
        if success:
            embed = discord.Embed(
                title="🎁 Weekly Reward Claimed",
                description=f"You successfully claimed your weekly reward of **{MONEY_EMOJI} {WEEKLY_REWARD:,}**!\n\nNew Cash Balance: **{MONEY_EMOJI} {result:,}**",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="⏳ Weekly Cooldown",
                description=f"You have already claimed your weekly reward!\n\nPlease wait **{format_days_hours(result)}** before claiming again.",
                color=discord.Color.gold(),
            )
        await message.channel.send(embed=embed, view=StandardLinksView())

    elif command == "ako":
        await asyncio.sleep(1)
        target = message.mentions[0] if message.mentions else message.author
        embed = format_meme_embed(target)
        await message.channel.send(embed=embed)

    elif client.user.mentioned_in(message) and not message.mention_everyone:
        await asyncio.sleep(1)
        target = message.author
        embed = format_meme_embed(target)
        await message.channel.send(embed=embed)

    elif user_text in ("ashop", "ash"):
        embed, view = create_main_shop_embed(message.author.id)
        await message.channel.send(embed=embed, view=view)

    elif user_text == "arkcode":
        embed = discord.Embed(
            title="🎁 • | MYSTERY CODE SHOP & REWARDS",
            description=(
                "🌟 Welcome to the Premium Mystery Code Center!\n\n"
                f"• **Price per Code:** `1,000,000 {MONEY_EMOJI}`\n"
                "• **Available Actions:**\n"
                "  - Click **🛒 Buy Code** to purchase codes in bulk (1 Code = 1M, 2 Codes = 2M, etc.).\n"
                "  - Click **🎁 Redeem Code** to enter your secret code and win instant rewards!\n\n"
                "✨ *Test your luck now to win Rare Backgrounds, Special AAA Items, or Mega Coins!*"
            ),
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=message.author.display_avatar.url)
        
        view = ArkCodeDashboardView(message.author.id)
        await message.channel.send(embed=embed, view=view)

    elif user_text == "acode":
        if message.author.id != DEV_USER_ID:
            return
        
        embed = discord.Embed(
            title="🔐 Developer Secret Console",
            description="Secure developer control panel. Click **Execute** below to dispatch secure console data to your direct messages.",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"Developer Console • {message.author.display_name}", icon_url=message.author.display_avatar.url)
        
        dm_codes_text = "\n".join([f"`{c}`" for c in SECRET_BG_CODES.keys()])
        dm_embed = discord.Embed(
            title="🔐 Secure Developer Promo Codes",
            description=f"Active background promo codes (Unlock All):\n\n{dm_codes_text}",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        dm_embed.set_thumbnail(url=message.author.display_avatar.url)
        dm_embed.set_footer(text="Secure Console Dispatch", icon_url=message.author.display_avatar.url)

        view = AcodeApprovalView(message.author.id, dm_embed, client)
        await message.channel.send(embed=embed, view=view)

    elif command == "aadp":
        if message.author.id != DEV_USER_ID:
            return
        if not args:
            return await message.channel.send("⚠️ Usage: `aadp <amount>` or `aadp @user <amount>` or `aadp AAA 1000`", delete_after=5)
        
        target_user = message.mentions[0] if message.mentions else message.author
        
        clean_args = [a for a in args if not a.startswith("<@")]
        if not clean_args:
            return await message.channel.send("⚠️ Please specify an amount or item!", delete_after=5)

        is_bank = False
        if clean_args[0].lower() == "bank":
            is_bank = True
            clean_args.pop(0)

        if not clean_args:
            return await message.channel.send("⚠️ Please specify an amount or item!", delete_after=5)

        val_str = clean_args[0].upper()
        
        if val_str.startswith("AAA"):
            item_count = 1
            if len(clean_args) >= 2 and clean_args[1].isdigit():
                item_count = int(clean_args[1])
            
            embed = discord.Embed(
                title="✨ Admin Action Confirmation",
                description=f"Do you want to add **{item_count:,}** AAA items to user {target_user.mention}?",
                color=discord.Color.from_rgb(147, 112, 219)
            )
            view = AdminActionApprovalView(message.author.id, target_user.id, 0, True, item_count, False)
            await message.channel.send(embed=embed, view=view)
        else:
            try:
                multiplier = 1
                raw_val = val_str
                if raw_val.endswith("K"):
                    multiplier = 1_000
                    raw_val = raw_val[:-1]
                elif raw_val.endswith("M"):
                    multiplier = 1_000_000
                    raw_val = raw_val[:-1]
                elif raw_val.endswith("B"):
                    multiplier = 1_000_000_000
                    raw_val = raw_val[:-1]
                elif raw_val.endswith("T"):
                    multiplier = 1_000_000_000_000
                    raw_val = raw_val[:-1]
                
                amount = int(float(raw_val) * multiplier)
                target_type = "Bank" if is_bank else "Cash"
                embed = discord.Embed(
                    title="✨ Admin Action Confirmation",
                    description=f"Do you want to add **{MONEY_EMOJI} {amount:,}** ({target_type}) to user {target_user.mention}?",
                    color=discord.Color.from_rgb(147, 112, 219)
                )
                view = AdminActionApprovalView(message.author.id, target_user.id, amount, False, 0, is_bank)
                await message.channel.send(embed=embed, view=view)
            except ValueError:
                await message.channel.send("❌ Invalid amount specified.", delete_after=5)

    elif user_text == "aaddcode":
        embed = discord.Embed(
            title="🔑 Secret Promo Code Redemption Center",
            description="✨ Welcome to the Exclusive Promo Code Portal!\n\nClick the premium **Redeem Code** button below to enter your secret promo code and request developer verification to unlock all backgrounds!",
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_footer(text="Secure Promo System • Premium Experience")
        await message.channel.send(embed=embed, view=SecretCodeView(client))

    elif command in ("aup", "ap"):
        target = message.mentions[0] if message.mentions else message.author
        balance, bank, xp, level, chat_xp, voice_xp, aa_count = get_user_data(target.id)

        server_name = message.guild.name if message.guild else "Server"
        bg_filename = get_user_background_filename(target.id)
        ring_style = get_user_avatar_border(target.id)

        try:
            avatar_bytes = await target.display_avatar.with_size(512).read()
            server_icon_bytes = None
            if message.guild and message.guild.icon:
                try:
                    server_icon_bytes = await message.guild.icon.with_size(128).read()
                except discord.DiscordException:
                    server_icon_bytes = None

            async with profile_lock:
                try:
                    await asyncio.to_thread(
                        generate_profile_card,
                        avatar_bytes,
                        target.display_name,
                        level,
                        chat_xp,
                        voice_xp,
                        aa_count,
                        server_name,
                        server_icon_bytes,
                        "profile_card.png",
                        bg_filename,
                        ring_style,
                    )
                    await message.channel.send(file=discord.File("profile_card.png"))
                finally:
                    if os.path.exists("profile_card.png"):
                        os.remove("profile_card.png")
        except Exception:
            traceback.print_exc()
            await message.channel.send("Sorry, could not generate profile card.")

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOKEN is missing. Add TOKEN=your_bot_token to your .env file.")
    client.run(TOKEN)