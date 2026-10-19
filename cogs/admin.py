import asyncio
import io
import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs import (
    AVATAR_BORDERS,
    BACKGROUNDS,
    BOT_OWNER_ID,
    DEFAULT_BG,
    DEV_USER_ID,
    MAX_CURRENCY_CAP,
    MONEY_EMOJI,
    MYSTERY_CODE_PRICE,
    SECRET_BG_CODES,
    URL_DEVELOPER,
    URL_FAQ,
    URL_SUPPORT,
    StandardLinksView,
    add_balance,
    add_bank_balance,
    add_special_item,
    bulk_redeem_codes,
    buy_mystery_codes,
    clamp_currency,
    format_num,
    get_admin_for_target_user,
    get_all_tracked_dm_ids,
    get_tracked_dm,
    get_user_unused_code_count,
    is_dev,
    is_owner,
    record_tracked_dm,
    redeem_single_code,
    unlock_specific_background,
)
from cogs.profile import generate_welcome_card

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
    {"type": "bilingual", "en": "Outstanding move!", "kh": "ជាក្បាច់វាយលុកដ៏អស្ចារ្យ!"},
]


def format_meme_embed(target_user: discord.User) -> discord.Embed:
    meme = random.choice(MEME_QUOTES)
    if meme["type"] == "khmer":
        description_text = f"### {target_user.mention}\n\n**{meme['text']}**"
    else:
        description_text = f"### {target_user.mention}\n\n**{meme['en']}**\n**{meme['kh']}**"
    return discord.Embed(description=description_text, color=discord.Color.from_rgb(147, 112, 219))


class CustomWelcomeNoteModal(discord.ui.Modal, title="✨ Send Custom Welcome Announcement"):
    note_input = discord.ui.TextInput(
        label="Enter Welcome Note Message",
        placeholder="Type your custom announcement message here...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    def __init__(self, guild: discord.Guild, admin_user: discord.Member, client_ref):
        super().__init__()
        self.guild = guild
        self.admin_user = admin_user
        self.client_ref = client_ref

    async def on_submit(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)
        try:
            avatar_bytes = await self.admin_user.display_avatar.with_size(512).read()
            buf = await asyncio.to_thread(
                generate_welcome_card,
                avatar_bytes,
                self.admin_user.display_name,
                self.guild.name,
                None,  # In-memory BytesIO
            )

            custom_note = self.note_input.value.strip()
            embed = discord.Embed(
                title=f"🌸 Welcome to {self.guild.name}!",
                description=f"Hello {self.admin_user.mention}!\n\n{custom_note}\n\n*— Sent with love by Developer Phean Chanthean*",
                color=discord.Color.from_rgb(147, 112, 219),
            )
            embed.set_image(url="attachment://welcome_card.png")

            file = discord.File(buf, filename="welcome_card.png")
            await self.admin_user.send(embed=embed, file=file, view=StandardLinksView())
            await interaction.response.send_message(f"✅ DM sent successfully to **{self.admin_user}** (`{self.guild.name}`)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ DM failed: {e}", ephemeral=True)


class AdminSelectForDM(discord.ui.Select):
    def __init__(self, guild: discord.Guild, client_ref):
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
                description=f"Role: {role_type}"[:100],
            ))

        if not options:
            options.append(discord.SelectOption(label="No admin found", value="none"))

        super().__init__(placeholder="🛡️ Select Admin or Owner to DM...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)

        if self.values[0] == "none":
            return await interaction.response.send_message("⚠️ No valid admin found.", ephemeral=True)

        admin_id = int(self.values[0])
        admin_user = self.guild.get_member(admin_id) or await interaction.client.fetch_user(admin_id)

        if not admin_user:
            return await interaction.response.send_message("❌ Could not fetch admin user.", ephemeral=True)

        await interaction.response.send_modal(CustomWelcomeNoteModal(self.guild, admin_user, self.client_ref))


class AdminSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, client_ref):
        super().__init__(timeout=300)
        self.guild = guild
        self.client_ref = client_ref
        self.add_item(AdminSelectForDM(guild, client_ref))

    @discord.ui.button(label="🔙 Back to Server List", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_servers(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)
        embed, view = create_dev_startup_embed_and_view(self.client_ref, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)


class ServerSelect(discord.ui.Select):
    def __init__(self, guilds):
        options = []
        for g in guilds[:25]:
            desc = f"Owner: {g.owner} | Members: {g.member_count}"
            options.append(discord.SelectOption(label=g.name[:100], value=str(g.id), description=desc[:100]))

        super().__init__(placeholder="🌐 Select a server to manage...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Checking admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)

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
            color=discord.Color.from_rgb(147, 112, 219),
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
    def __init__(self, guild_id: int, client_ref):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.client_ref = client_ref

    @discord.ui.button(label="📩 Send DM to Admin/Owner", style=discord.ButtonStyle.primary, row=0)
    async def dm_admin_prompt(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)

        guild = self.client_ref.get_guild(self.guild_id)
        if not guild:
            return await interaction.response.send_message("❌ Server not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"🌸 Select Admin/Owner in {guild.name}",
            description="Select an administrator from the dropdown menu to send a customized welcome DM.",
            color=discord.Color.from_rgb(147, 112, 219),
        )
        view = AdminSelectView(guild, self.client_ref)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🚪 Leave Server", style=discord.ButtonStyle.danger, row=0)
    async def leave_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)

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

            new_view = DevDashboardView(self.client_ref.guilds, self.client_ref.user.id, client_ref=self.client_ref, user_id=interaction.user.id)
            await interaction.message.edit(embed=embed, view=new_view)
            await interaction.response.send_message(f"✅ Successfully left server **{guild_name}**!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to leave server: {e}", ephemeral=True)

    @discord.ui.button(label="🔙 Back to Server List", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_owner(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized: Managing admin servers is restricted strictly to the **Bot Owner ONLY**.", ephemeral=True)

        embed, view = create_dev_startup_embed_and_view(self.client_ref, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)


class DevDashboardView(discord.ui.View):
    def __init__(self, guilds, client_id: int, client_ref=None, user_id: int = None):
        super().__init__(timeout=300)
        self.client_ref = client_ref
        self.user_id = user_id
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot"
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="➕ Add Server", url=invite_url))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ))

        # Check Admin Servers dropdown is restricted to Bot Owner ONLY
        if guilds and (user_id is None or is_owner(user_id)):
            self.add_item(ServerSelect(guilds))

    @discord.ui.button(label="📖 Command Guide", style=discord.ButtonStyle.success, row=3)
    async def show_help_guide(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
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
                "• 50% chance of success, steal 10–35% of their cash\n"
                "• Caught? You pay 5–15% of *your* cash to the victim\n"
                "• Bank funds are 100% safe from robbery"
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
            name="✨ Mystery Codes & Promo",
            value=(
                "`arkcode` or `atc` — Open Mystery Code Shop\n"
                "• Buy codes, redeem single codes, or Auto-Open in bulk\n"
                "• Win coins, avatar borders, backgrounds, or AAA\n"
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
            name="🔐 Developer & Owner Only",
            value=(
                "`send <User_ID> <Description>` + [File] — DM user with text & file (👑 Owner Only)\n"
                "`aservers` — Check connected admin servers (👑 Owner Only)\n"
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
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Unauthorized.", ephemeral=True)
        if self.client_ref:
            embed, view = create_dev_startup_embed_and_view(self.client_ref, interaction.user.id)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("⚠️ Cannot refresh — client reference unavailable.", ephemeral=True)


def create_dev_startup_embed_and_view(client_ref, user_id: int = None):
    guilds = client_ref.guilds
    total_members = sum(g.member_count for g in guilds)
    total_bots = sum(1 for g in guilds for m in g.members if m.bot)
    total_humans = total_members - total_bots

    top_guilds = sorted(guilds, key=lambda g: g.member_count, reverse=True)[:5]
    top_list = "\n".join(
        f"> `{i+1}.` **{g.name}** — `{g.member_count:,}` members"
        for i, g in enumerate(top_guilds)
    )

    owner_session = user_id is None or is_owner(user_id)
    quick_actions = [
        "▸ **Select a server** from dropdown to check admin servers" if owner_session else None,
        "▸ **📖 Command Guide** — View all bot commands",
        "▸ **🔙 Refresh** — Reload dashboard statistics",
        "▸ **➕ Add Server** — Invite the bot to a new server",
    ]
    quick_actions_text = "\n".join(a for a in quick_actions if a)

    desc_extra = (
        "Use the dropdown below to check admin servers, or tap **📖 Command Guide** for reference."
        if owner_session
        else "Tap **📖 Command Guide** for the full reference."
    )

    embed = discord.Embed(
        title="⚡ PREMIUM DEVELOPER DASHBOARD",
        description=(
            "```\n"
            "  Bot Status: ● ONLINE & OPERATIONAL\n"
            "```\n"
            "Welcome back. All systems are running normally.\n"
            f"{desc_extra}"
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
        value=quick_actions_text,
        inline=False,
    )
    embed.set_footer(text="Ark Bot • Premium Dashboard • Developed by Phean Chanthean")

    view = DevDashboardView(guilds, client_ref.user.id, client_ref=client_ref, user_id=user_id)
    return embed, view


class AdminActionApprovalView(discord.ui.View):
    def __init__(self, dev_id: int, target_user_id: int, amount: int, is_item: bool, item_count: int, is_bank: bool = False):
        super().__init__(timeout=180)
        self.dev_id = dev_id
        self.target_user_id = target_user_id
        self.amount = amount
        self.is_item = is_item
        self.item_count = item_count
        self.is_bank = is_bank

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Unauthorized action.", ephemeral=True)
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message(f"⚠️ {interaction.user.mention} This confirmation session belongs to someone else.", ephemeral=True)

        if self.is_item:
            item_cnt = clamp_currency(self.item_count)
            add_special_item(self.target_user_id, item_cnt)
            msg = f"✅ {interaction.user.mention} Successfully added **{format_num(item_cnt)}** ({item_cnt:,}) AAA items to user ID `{self.target_user_id}`!"
        elif self.is_bank:
            amt = clamp_currency(self.amount)
            add_bank_balance(self.target_user_id, amt)
            msg = f"✅ {interaction.user.mention} Successfully added **{MONEY_EMOJI} {format_num(amt)}** ({amt:,}) to Bank of user ID `{self.target_user_id}`!"
        else:
            amt = clamp_currency(self.amount)
            add_balance(self.target_user_id, amt)
            msg = f"✅ {interaction.user.mention} Successfully added **{MONEY_EMOJI} {format_num(amt)}** ({amt:,}) to Cash of user ID `{self.target_user_id}`!"

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✨ ADMIN ACTION: ACCEPTED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Unauthorized action.", ephemeral=True)
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message(f"⚠️ {interaction.user.mention} This confirmation session belongs to someone else.", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ ADMIN ACTION: CANCELLED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"⚠️ {interaction.user.mention} Admin action cancelled.", ephemeral=True)


class AcodeApprovalView(discord.ui.View):
    def __init__(self, dev_id: int, embed_data: discord.Embed, client_ref):
        super().__init__(timeout=180)
        self.dev_id = dev_id
        self.embed_data = embed_data
        self.client_ref = client_ref

    @discord.ui.button(label="Execute", style=discord.ButtonStyle.success, emoji="✅")
    async def execute_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Unauthorized action.", ephemeral=True)
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message(f"⚠️ {interaction.user.mention} This console session belongs to someone else.", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✨ ACODE EXECUTED & POSTED TO DM"
        await interaction.message.edit(embed=embed, view=self)

        try:
            dev_user = await self.client_ref.fetch_user(self.dev_id)
            await dev_user.send(embed=self.embed_data)
            await interaction.response.send_message(f"✅ {interaction.user.mention} Successfully posted to your DM!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send DM: {e}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Unauthorized action.", ephemeral=True)
        if interaction.user.id != self.dev_id:
            return await interaction.response.send_message(f"⚠️ {interaction.user.mention} This console session belongs to someone else.", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ ACODE CANCELLED"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"⚠️ {interaction.user.mention} Action cancelled.", ephemeral=True)


class SecretCodeApprovalView(discord.ui.View):
    def __init__(self, dev_id: int, target_user_id: int, code: str, client_ref):
        super().__init__(timeout=300)
        self.dev_id = dev_id
        self.target_user_id = target_user_id
        self.code = code
        self.client_ref = client_ref

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_redeem(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_dev(interaction.user.id):
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
                    color=discord.Color.gold(),
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
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)

        try:
            target_user = await self.client_ref.fetch_user(self.target_user_id)
            if target_user:
                fail_embed = discord.Embed(
                    title="❌ UNLOCK ALL BACKGROUNDS REJECTED",
                    description=f"Sorry, your submitted code `{self.code}` was rejected by the developer.",
                    color=discord.Color.red(),
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
        max_length=50,
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
                color=discord.Color.red(),
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
                    color=discord.Color.from_rgb(147, 112, 219),
                )
                req_embed.set_thumbnail(url=user.display_avatar.url)
                req_embed.set_footer(text=f"Requested by {user.display_name}", icon_url=user.display_avatar.url)

                view = SecretCodeApprovalView(DEV_USER_ID, user.id, entered_code, self.client_ref)
                await dev_user.send(embed=req_embed, view=view)

            embed = discord.Embed(
                title="⏳ Request Sent to Developer",
                description=f"Your code `{entered_code}` has been submitted for developer verification! You will be notified once approved.",
                color=discord.Color.from_rgb(147, 112, 219),
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


# ==========================================
# 🌸 KAWAII AESTHETIC ARKCODE (MYSTERY CODE) SYSTEM 🌸
# ==========================================
KAWAII_PINK = discord.Color.from_rgb(255, 183, 197)      # #FFB7C5 Soft Pastel Pink
KAWAII_PURPLE = discord.Color.from_rgb(216, 180, 254)    # #D8B4FE Soft Lavender
KAWAII_BLUE = discord.Color.from_rgb(186, 230, 253)      # #BAE6FD Baby Sky Blue
KAWAII_GOLD = discord.Color.from_rgb(254, 240, 138)      # #FEF08A Sparkle Gold


def build_arkcode_main_embed(user: discord.User | discord.Member) -> discord.Embed:
    """Builds the minimal Mystery Code Shop embed."""
    unused_count = get_user_unused_code_count(user.id)
    embed = discord.Embed(
        title="Mystery Code Shop",
        description=(
            f"🏷️ **Price:** `{MYSTERY_CODE_PRICE:,} 🔷`\n"
            f"🎒 **Unused Codes:** `{unused_count}`\n\n"
            "🔷 Coins\n"
            "🖼️ Avatar Border\n"
            "🌌 Background\n"
            "💎 AAA"
        ),
        color=KAWAII_PINK,
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"Requested by {user.display_name}")
    return embed


def create_bulk_rewards_embed(user: discord.User | discord.Member, result: dict) -> discord.Embed:
    """Builds the simplified unboxing result embed."""
    total_coins = result.get("total_coins", 0)
    total_aaa = result.get("total_aaa", 0)
    bgs_won = result.get("bgs_won", [])
    borders_won = result.get("borders_won", [])

    lines = [
        f"- 🔷 {total_coins:,} Coins",
        f"- 💎 {total_aaa:,} AAA",
    ]
    for bg in bgs_won:
        name = bg["name"] if isinstance(bg, dict) else str(bg)
        lines.append(f"- 🌌 Background: {name}")
    for border in borders_won:
        name = border["name"] if isinstance(border, dict) else str(border)
        lines.append(f"- 🖼️ Avatar Border: {name}")

    embed = discord.Embed(
        title="Unboxing Result",
        description="\n".join(lines),
        color=KAWAII_PINK,
    )
    embed.set_footer(text=f"Opened by {user.display_name}")
    return embed


class BuyCodeQuantityModal(discord.ui.Modal, title="🌸 Buy Mystery Codes 🛒"):
    qty_input = discord.ui.TextInput(
        label="How many codes would you like? 🎀",
        placeholder="e.g. 1, 5, 10, 50... (1 Code = 1,000,000 🔷)",
        required=True,
        max_length=5,
    )

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        try:
            qty = int(self.qty_input.value.strip())
            if qty <= 0:
                raise ValueError()
        except ValueError:
            return await interaction.response.send_message(
                "🌸 (｡•́︿•̀｡) Oopsie! Please enter a valid positive number! 🎀", ephemeral=True
            )

        res = buy_mystery_codes(self.user_id, qty)
        if not res["success"]:
            if res.get("error") == "insufficient_funds":
                needed = res["needed"]
                bal = res["balance"]
                embed = discord.Embed(
                    title="💸 Oopsie! Insufficient Coins 🌸",
                    description=(
                        f"(｡•́︿•̀｡) Aww! You need **{MONEY_EMOJI} {needed:,}** for **{qty}** code(s),\n"
                        f"but you currently only have **{MONEY_EMOJI} {bal:,}** cash on hand! 🎀\n\n"
                        "✨ *Tip: Collect daily rewards or win games to earn more coins!*"
                    ),
                    color=KAWAII_PINK,
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            return await interaction.response.send_message("❌ Failed to purchase codes. Please try again!", ephemeral=True)

        embed = discord.Embed(
            title="🎀 ✨ Purchase Successful! ✨ 🎀",
            description=(
                f"(◕‿◕)♡ Yay! You acquired **`{qty}`** Mystery Code(s)! 🎁\n\n"
                "╭────────────────────────╮\n"
                f"│  💸 **Total Spent:** `{MONEY_EMOJI} {format_num(res['total_price'])}` ({res['total_price']:,})\n"
                f"│  💳 **Remaining Cash:** `{MONEY_EMOJI} {format_num(res['new_balance'])}`\n"
                f"│  🎒 **Backpack Total:** **`{res['total_unused']}`** Unused Code(s) ✨\n"
                "╰────────────────────────╯\n\n"
                "🪄 **All codes have been safely tucked into your inventory!**\n"
                "Click **🪄 Auto Open Codes** to open them with fairy magic! 🌸💖"
            ),
            color=KAWAII_PINK,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(
            text=f"Purchased with love by {interaction.user.display_name} 🌸",
            icon_url=interaction.user.display_avatar.url,
        )
        view = PostBuyView(self.user_id, res["total_unused"])
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RedeemCodeModal(discord.ui.Modal, title="🔑 Redeem 1 Mystery Code ✨"):
    code_input = discord.ui.TextInput(
        label="Mystery Code (Leave blank for backpack code)",
        placeholder="e.g. ARK-XXXX-XXXX or leave empty 🌸",
        required=False,
        max_length=50,
    )

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        code_str = self.code_input.value.strip() if self.code_input.value else None
        res = redeem_single_code(self.user_id, code_str)

        if not res["success"]:
            err = res.get("error")
            if err == "no_codes":
                embed = discord.Embed(
                    title="🎒 Empty Backpack Notice 🌸",
                    description=(
                        "(｡•́︿•̀｡) You didn't enter a code and have no unused codes in your backpack!\n\n"
                        "Click **🛒 Buy Codes** to grab one, or type a code into the box! 🎀✨"
                    ),
                    color=KAWAII_PINK,
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            elif err == "not_found":
                return await interaction.response.send_message("❌ (｡•́︿•̀｡) Invalid code! Please check for typos and try again 🌸", ephemeral=True)
            elif err == "already_used":
                return await interaction.response.send_message("⚠️ (｡•́︿•̀｡) This mystery code has already been redeemed! 🌸", ephemeral=True)
            return await interaction.response.send_message(f"❌ Failed to redeem code: {err}", ephemeral=True)

        reward = res["reward"]
        rem = res["remaining_codes"]

        total_coins = reward["amount"] if reward["type"] == "coins" else 0
        total_aaa = reward["amount"] if reward["type"] == "aaa" else 0
        bgs_won = [reward] if reward["type"] == "background" else []
        borders_won = [reward] if reward["type"] == "border" else []

        single_result = {
            "total_coins": total_coins,
            "total_aaa": total_aaa,
            "bgs_won": bgs_won,
            "borders_won": borders_won,
            "remaining_codes": rem,
        }
        embed = create_bulk_rewards_embed(interaction.user, single_result)
        view = PostUnboxView(self.user_id, rem)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CustomAutoOpenModal(discord.ui.Modal, title="🪄 Custom Auto-Open Amount 🎀"):
    def __init__(self, user_id: int, max_available: int):
        super().__init__()
        self.user_id = user_id
        self.max_available = max_available
        self.amount_input = discord.ui.TextInput(
            label=f"How many codes? (Max {max_available}) 🌸",
            placeholder=f"Enter a number between 1 and {max_available}...",
            required=True,
            max_length=6,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        try:
            amount = int(self.amount_input.value.strip())
            if amount <= 0:
                raise ValueError()
        except ValueError:
            return await interaction.response.send_message("🌸 (｡•́︿•̀｡) Please enter a valid number! 🎀", ephemeral=True)

        if amount > self.max_available:
            amount = self.max_available

        res = bulk_redeem_codes(self.user_id, amount)
        if not res["success"]:
            return await interaction.response.send_message(f"❌ Failed to auto-open codes: {res.get('error')}", ephemeral=True)

        summary_embed = create_bulk_rewards_embed(interaction.user, res)
        post_view = PostUnboxView(self.user_id, res["remaining_codes"])
        try:
            await interaction.response.edit_message(embed=summary_embed, view=post_view)
        except Exception:
            await interaction.response.send_message(embed=summary_embed, view=post_view, ephemeral=True)


class AutoOpenDropdown(discord.ui.Select):
    def __init__(self, user_id: int, total_available: int):
        self.user_id = user_id
        self.total_available = total_available

        options = []
        tiers = [1, 5, 10, 25, 50, 100]
        for t in tiers:
            if t < total_available:
                options.append(
                    discord.SelectOption(
                        label=f"🎀 Open {t} Code(s)",
                        value=f"bundle_{t}",
                        description=f"Instantly unbox {t} code(s) with fairy magic! ✨",
                        emoji="🌸",
                    )
                )

        options.append(
            discord.SelectOption(
                label=f"✨ Open All ({total_available} Code{'s' if total_available > 1 else ''})",
                value=f"bundle_{total_available}",
                description=f"Magically unbox all {total_available} code(s) at once! 💖",
                emoji="🎁",
            )
        )

        super().__init__(
            placeholder="✨ Choose a bulk opening bundle... 🌸",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        chosen = int(self.values[0].replace("bundle_", ""))
        res = bulk_redeem_codes(self.user_id, chosen)
        if not res["success"]:
            return await interaction.response.send_message(f"❌ Failed to auto-open codes: {res.get('error')}", ephemeral=True)

        summary_embed = create_bulk_rewards_embed(interaction.user, res)
        post_view = PostUnboxView(self.user_id, res["remaining_codes"])
        try:
            await interaction.response.edit_message(embed=summary_embed, view=post_view)
        except Exception:
            await interaction.response.send_message(embed=summary_embed, view=post_view, ephemeral=True)


class AutoOpenSelectorView(discord.ui.View):
    def __init__(self, user_id: int, total_available: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.total_available = total_available

        # Row 0: Aesthetic Dropdown Select Menu
        self.add_item(AutoOpenDropdown(user_id, total_available))

        # Row 1: Interactive Quick Buttons
        if total_available >= 10:
            btn_10 = discord.ui.Button(label="🎀 Open 10", style=discord.ButtonStyle.primary, row=1)
            btn_10.callback = self.make_button_callback(10)
            self.add_item(btn_10)

        if total_available >= 50:
            btn_50 = discord.ui.Button(label="🌸 Open 50", style=discord.ButtonStyle.primary, row=1)
            btn_50.callback = self.make_button_callback(50)
            self.add_item(btn_50)

        btn_all = discord.ui.Button(
            label=f"✨ Open All ({total_available})",
            style=discord.ButtonStyle.success,
            row=1,
        )
        btn_all.callback = self.make_button_callback(total_available)
        self.add_item(btn_all)

        btn_custom = discord.ui.Button(
            label="✏️ Custom Amount",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        btn_custom.callback = self.custom_button_callback
        self.add_item(btn_custom)

    def make_button_callback(self, count: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

            res = bulk_redeem_codes(self.user_id, count)
            if not res["success"]:
                return await interaction.response.send_message(f"❌ Failed to auto-open codes: {res.get('error')}", ephemeral=True)

            summary_embed = create_bulk_rewards_embed(interaction.user, res)
            post_view = PostUnboxView(self.user_id, res["remaining_codes"])
            try:
                await interaction.response.edit_message(embed=summary_embed, view=post_view)
            except Exception:
                await interaction.response.send_message(embed=summary_embed, view=post_view, ephemeral=True)

        return callback

    async def custom_button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)
        await interaction.response.send_modal(CustomAutoOpenModal(self.user_id, self.total_available))


class PostUnboxView(discord.ui.View):
    def __init__(self, user_id: int, remaining_codes: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.remaining_codes = remaining_codes

        if remaining_codes > 0:
            open_more_btn = discord.ui.Button(
                label=f"🪄 Open More ({remaining_codes} left)",
                style=discord.ButtonStyle.primary,
                emoji="🎀",
                row=0,
            )
            open_more_btn.callback = self.open_more_callback
            self.add_item(open_more_btn)

        buy_more_btn = discord.ui.Button(
            label="🛒 Buy More Codes",
            style=discord.ButtonStyle.success,
            emoji="🌸",
            row=0,
        )
        buy_more_btn.callback = self.buy_more_callback
        self.add_item(buy_more_btn)

    async def open_more_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        current_rem = get_user_unused_code_count(self.user_id)
        if current_rem <= 0:
            return await interaction.response.send_message("🌸 (｡•́︿•̀｡) You don't have any codes left in your backpack! 🎀", ephemeral=True)

        embed = discord.Embed(
            title="🪄 ✨ 𝐀𝐔𝐓𝐎-𝐎𝐏𝐄𝐍 𝐌𝐘𝐒𝐓𝐄𝐑𝐘 𝐂𝐎𝐃𝐄𝐒 ✨ 🪄",
            description=(
                f"(｡♥‿♥｡) Yay! You still have **`{current_rem}`** unused mystery code(s) ready! 🎒🌸\n\n"
                "Select how many codes you want our magical fairy to unbox instantly for you: 🪄🎀"
            ),
            color=KAWAII_PURPLE,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Magical unboxing queue • {current_rem} code(s) ready! 🌸")
        view = AutoOpenSelectorView(self.user_id, current_rem)
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def buy_more_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)
        await interaction.response.send_modal(BuyCodeQuantityModal(self.user_id))


class PostBuyView(discord.ui.View):
    def __init__(self, user_id: int, total_unused: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.total_unused = total_unused

        open_btn = discord.ui.Button(
            label=f"🪄 Auto Open ({total_unused} Codes)",
            style=discord.ButtonStyle.primary,
            emoji="✨",
            row=0,
        )
        open_btn.callback = self.open_callback
        self.add_item(open_btn)

    async def open_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session is not yours!", ephemeral=True)

        current_rem = get_user_unused_code_count(self.user_id)
        if current_rem <= 0:
            return await interaction.response.send_message("🌸 You don't have any codes left! 🎀", ephemeral=True)

        embed = discord.Embed(
            title="🪄 ✨ 𝐀𝐔𝐓𝐎-𝐎𝐏𝐄𝐍 𝐌𝐘𝐒𝐓𝐄𝐑𝐘 𝐂𝐎𝐃𝐄𝐒 ✨ 🪄",
            description=(
                f"(｡♥‿♥｡) Yay! You have **`{current_rem}`** unused mystery code(s) ready! 🎒🌸\n\n"
                "Select how many codes you want our magical fairy to unbox instantly for you: 🪄🎀"
            ),
            color=KAWAII_PURPLE,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Magical unboxing queue • {current_rem} code(s) ready! 🌸")
        view = AutoOpenSelectorView(self.user_id, current_rem)
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ArkCodeDashboardView(discord.ui.View):
    """The 3 Aesthetic Buttons for the Kawaii Mystery Code Sanctuary."""

    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    # 1. 🛒 Buy Codes (Green / Success)
    @discord.ui.button(label="🛒 Buy Codes", style=discord.ButtonStyle.success, row=0)
    async def buy_code_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session belongs to someone else!", ephemeral=True)
        await interaction.response.send_modal(BuyCodeQuantityModal(self.user_id))

    # 2. 🔑 Redeem 1 Code (Gray / Secondary)
    @discord.ui.button(label="🔑 Redeem 1 Code", style=discord.ButtonStyle.secondary, row=0)
    async def redeem_code_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session belongs to someone else!", ephemeral=True)
        await interaction.response.send_modal(RedeemCodeModal(self.user_id))

    # 3. 🪄 Auto Open Codes (Blurple / Primary) - New Feature!
    @discord.ui.button(label="🪄 Auto Open Codes", style=discord.ButtonStyle.primary, row=0)
    async def auto_open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🎀 (｡•́︿•̀｡) This session belongs to someone else!", ephemeral=True)

        unused_count = get_user_unused_code_count(self.user_id)
        if unused_count <= 0:
            embed = discord.Embed(
                title="🌸 Aww, Your Backpack is Empty! 🎒✨",
                description=(
                    "(๑>ᴗ<๑) You don't have any unused mystery codes in your backpack yet! 🎀\n\n"
                    "Click **🛒 Buy Codes** to purchase some shiny codes first,\n"
                    "then come right back to auto-open them in a magical flash! 💖🪄"
                ),
                color=KAWAII_PINK,
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Fairy Tip: Each code holds magical surprises! ✨")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="🪄 ✨ 𝐀𝐔𝐓𝐎-𝐎𝐏𝐄𝐍 𝐌𝐘𝐒𝐓𝐄𝐑𝐘 𝐂𝐎𝐃𝐄𝐒 ✨ 🪄",
            description=(
                f"(｡♥‿♥｡) Yay! You currently have **`{unused_count}`** unused mystery code(s) ready! 🎒🌸\n\n"
                "Select how many codes you want our magical fairy to unbox instantly for you:\n"
                "*(No manual typing required — all rewards are safely added to your account!)* 🪄🎀"
            ),
            color=KAWAII_PURPLE,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Magical unboxing queue • {unused_count} code(s) ready! 🌸")
        view = AutoOpenSelectorView(self.user_id, unused_count)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CallableBool(int):
    """A boolean-compatible integer that is also callable as a function with zero arguments.
    Allows both `if view.is_finished:` and `if view.is_finished():` to work seamlessly
    without raising TypeError.
    """
    def __new__(cls, val: bool = False):
        return super().__new__(cls, 1 if val else 0)

    def __call__(self) -> bool:
        return bool(self)

    def __bool__(self) -> bool:
        return bool(int(self))


class SendConfirmationView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        admin_cog: "Admin",
        admin_id: int,
        target_user: discord.User,
        description: str,
        attachment_data: list[tuple[str, bytes, str | None]],
        size_mb: float,
        timeout: float = 300.0,
    ):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.admin_cog = admin_cog
        self.admin_id = admin_id
        self.target_user = target_user
        self.description = description
        self.attachment_data = attachment_data
        self.size_mb = size_mb
        self._is_action_done = False

    @property
    def is_finished(self) -> CallableBool:
        """Property for button tracking. Works both with and without parentheses."""
        done = getattr(self, "_is_action_done", False) or super().is_finished()
        return CallableBool(done)

    @is_finished.setter
    def is_finished(self, value):
        self._is_action_done = bool(value)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                f"❌ {interaction.user.mention} This confirmation prompt is restricted to the administrator who initiated it.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Accept/Send", emoji="✅", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_finished:
            return
        self.is_finished = True
        self.stop()

        await interaction.response.defer()

        files = []
        for filename, data, desc in self.attachment_data:
            files.append(discord.File(fp=io.BytesIO(data), filename=filename, description=desc))

        try:
            dm_channel = self.target_user.dm_channel or await self.target_user.create_dm()
            if files:
                sent_dm = await dm_channel.send(
                    content=self.description if self.description else None,
                    files=files,
                )
            else:
                sent_dm = await dm_channel.send(content=self.description)

            # Record in DB and memory
            record_tracked_dm(
                message_id=sent_dm.id,
                target_user_id=self.target_user.id,
                admin_id=self.admin_id,
                description=self.description or "",
            )
            self.admin_cog.add_tracked_dm(sent_dm.id, self.target_user.id)

            success_embed = discord.Embed(
                title="✅ Sent Successfully!",
                description=(
                    f"Direct message has been delivered to **{self.target_user.display_name}** (<@{self.target_user.id}>).\n"
                    f"All command triggers and sender identity were kept completely hidden."
                ),
                color=discord.Color.from_rgb(46, 204, 113),
            )
            success_embed.add_field(
                name="🎯 Target User ID",
                value=f"<@{self.target_user.id}> (`{self.target_user.id}`)",
                inline=True,
            )
            file_summary = (
                f"**{self.size_mb:.2f} MB** ({len(self.attachment_data)} file(s))"
                if self.attachment_data
                else "None (0.00 MB)"
            )
            success_embed.add_field(
                name="📦 Attached File Size",
                value=file_summary,
                inline=True,
            )
            if self.description:
                desc_display = self.description if len(self.description) <= 300 else self.description[:297] + "..."
                success_embed.add_field(
                    name="📝 Description Text",
                    value=f"> {desc_display}",
                    inline=False,
                )
            success_embed.add_field(
                name="📡 Two-Way Tracking Active",
                value=(
                    "• **Reactions:** You will be notified immediately if the recipient reacts to this DM.\n"
                    "• **Replies:** Any direct reply from the recipient will be forwarded straight to your DM."
                ),
                inline=False,
            )
            success_embed.set_footer(
                text=f"DM ID: {sent_dm.id} • Sent Successfully",
                icon_url=self.target_user.display_avatar.url,
            )

            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=None,
                embed=success_embed,
                view=None,
            )

        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Delivery Failed (DMs Closed)",
                description=(
                    f"Could not send DM to **{self.target_user.display_name}** (`{self.target_user.id}`).\n"
                    f"Their direct messages are closed or they have blocked the bot."
                ),
                color=discord.Color.from_rgb(235, 75, 75),
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=None,
                embed=error_embed,
                view=None,
            )
        except discord.HTTPException as e:
            error_embed = discord.Embed(
                title="❌ Delivery Failed (Discord HTTP Error)",
                description=f"Discord returned an error when uploading the message:\n```{e}```",
                color=discord.Color.from_rgb(235, 75, 75),
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=None,
                embed=error_embed,
                view=None,
            )
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Delivery Failed",
                description=f"An unexpected error occurred while dispatching the DM:\n```{e}```",
                color=discord.Color.from_rgb(235, 75, 75),
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=None,
                embed=error_embed,
                view=None,
            )

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_finished:
            return
        self.is_finished = True
        self.stop()

        cancel_embed = discord.Embed(
            title="🛑 Operation Cancelled",
            description=f"**Operation Cancelled.** The direct message was aborted and not sent to <@{self.target_user.id}>.",
            color=discord.Color.from_rgb(108, 117, 125),
        )
        cancel_embed.add_field(
            name="🎯 Target User ID",
            value=f"<@{self.target_user.id}> (`{self.target_user.id}`)",
            inline=True,
        )
        cancel_embed.add_field(
            name="📦 Attached File Size",
            value=f"**{self.size_mb:.2f} MB**",
            inline=True,
        )
        cancel_embed.set_footer(text="Cancelled by Administrator")
        await interaction.response.edit_message(
            content=None,
            embed=cancel_embed,
            view=None,
        )

    async def on_timeout(self):
        if not self.is_finished:
            self.is_finished = True
            for item in self.children:
                item.disabled = True


class Admin(commands.Cog):
    """Developer commands, server management dashboard, and fun social utilities."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_spam_tasks = {}
        tracked_msg_ids, tracked_user_ids = get_all_tracked_dm_ids()
        self.tracked_dm_message_ids = tracked_msg_ids
        self.tracked_target_user_ids = tracked_user_ids

    def add_tracked_dm(self, message_id: int, target_user_id: int):
        self.tracked_dm_message_ids.add(message_id)
        self.tracked_target_user_ids.add(target_user_id)

    def is_dm_tracked(self, message_id: int) -> bool:
        return message_id in self.tracked_dm_message_ids

    def is_target_user_tracked(self, user_id: int) -> bool:
        return user_id in self.tracked_target_user_ids

    def cog_unload(self):
        for task in self.active_spam_tasks.values():
            task.cancel()
        self.active_spam_tasks.clear()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore bot's own reactions
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        if not self.is_dm_tracked(payload.message_id):
            return

        record = get_tracked_dm(payload.message_id)
        admin_id = record["admin_id"] if record and record.get("admin_id") else BOT_OWNER_ID

        try:
            admin_user = self.bot.get_user(admin_id) or await self.bot.fetch_user(admin_id)
        except Exception:
            admin_user = None

        if not admin_user:
            return

        try:
            reacting_user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)
            user_display = f"{reacting_user.mention} (`{reacting_user.name}` | ID: `{payload.user_id}`)"
            avatar_url = reacting_user.display_avatar.url
        except Exception:
            user_display = f"<@{payload.user_id}> (ID: `{payload.user_id}`)"
            avatar_url = None

        emoji_str = str(payload.emoji)
        desc_snippet = record.get("description", "") if record else ""
        if len(desc_snippet) > 200:
            desc_snippet = desc_snippet[:197] + "..."

        embed = discord.Embed(
            title="🔔 Recipient Reacted to DM",
            description="The recipient reacted to your tracked direct message!",
            color=discord.Color.from_rgb(255, 105, 180),
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.add_field(name="👤 Reacted By", value=user_display, inline=False)
        embed.add_field(name="✨ Emoji Used", value=f"### {emoji_str} (`{emoji_str}`)", inline=True)
        embed.add_field(name="🆔 DM Message ID", value=f"`{payload.message_id}`", inline=True)
        if desc_snippet:
            embed.add_field(name="📝 Original Message Description", value=f"> {desc_snippet}", inline=False)

        embed.set_footer(text="Two-Way DM Communication System • Reaction Tracker")

        try:
            dm_channel = admin_user.dm_channel or await admin_user.create_dm()
            await dm_channel.send(embed=embed)
        except Exception as e:
            print(f"[Reaction Tracker] Failed to alert admin {admin_id}: {e}")

    async def forward_dm_reply(self, message: discord.Message, referenced_msg_id: int | None):
        admin_id = None
        record = None
        if referenced_msg_id:
            record = get_tracked_dm(referenced_msg_id)
            if record and record.get("admin_id"):
                admin_id = record["admin_id"]

        if not admin_id:
            admin_id = get_admin_for_target_user(message.author.id)

        try:
            admin_user = self.bot.get_user(admin_id) or await self.bot.fetch_user(admin_id)
        except Exception:
            admin_user = None

        if not admin_user:
            return

        embed = discord.Embed(
            title="📨 Direct Reply Received",
            description=f"Recipient {message.author.mention} (`{message.author.name}`) sent a direct reply to the bot!",
            color=discord.Color.from_rgb(52, 152, 219),
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(
            name="👤 Sender",
            value=f"{message.author.mention} (`{message.author.name}` | ID: `{message.author.id}`)",
            inline=False,
        )

        content_text = message.content.strip()
        if content_text:
            embed.add_field(
                name="💬 Reply Content",
                value=f"> {content_text}" if len(content_text) <= 1000 else f"> {content_text[:997]}...",
                inline=False,
            )
        else:
            embed.add_field(
                name="💬 Reply Content",
                value="*[No text content - Attachment only]*",
                inline=False,
            )

        if record and record.get("description"):
            orig_desc = record["description"]
            orig_disp = orig_desc if len(orig_desc) <= 200 else orig_desc[:197] + "..."
            embed.add_field(name="↩️ Replying To Original DM", value=f"> {orig_disp}", inline=False)
        elif referenced_msg_id:
            embed.add_field(name="↩️ Replying To Message ID", value=f"`{referenced_msg_id}`", inline=False)

        if message.attachments:
            att_info = "\n".join([f"• `{a.filename}` ({a.size / (1024 * 1024):.2f} MB)" for a in message.attachments])
            embed.add_field(name="📎 Attached Files", value=att_info, inline=False)

        embed.set_footer(
            text="Two-Way DM Communication System • Message Forwarder",
            icon_url=message.author.display_avatar.url,
        )

        # Convert attachments to forward
        forward_files = []
        for att in message.attachments:
            try:
                f = await att.to_file()
                forward_files.append(f)
            except Exception as e:
                print(f"[Forwarder] Failed to convert attachment {att.filename}: {e}")

        try:
            admin_dm = admin_user.dm_channel or await admin_user.create_dm()
            if forward_files:
                await admin_dm.send(embed=embed, files=forward_files)
            else:
                await admin_dm.send(embed=embed)
        except Exception as e:
            print(f"[Forwarder] Failed to forward DM reply to admin {admin_id}: {e}")

    @app_commands.command(name="update", description="✨ Open the bot startup premium dashboard and management panel")
    async def update_command(self, interaction: discord.Interaction):
        if not is_dev(interaction.user.id):
            return await interaction.response.send_message(f"❌ {interaction.user.mention} Sorry! This command is only available for Developers.", ephemeral=True)

        if interaction.guild is not None:
            return await interaction.response.send_message(f"🔒 {interaction.user.mention} This command can only be used in **Private DMs**!", ephemeral=True)

        embed, view = create_dev_startup_embed_and_view(interaction.client, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="arkcode", description="Open the Mystery Code Shop")
    async def arkcode_slash(self, interaction: discord.Interaction):
        embed = build_arkcode_main_embed(interaction.user)
        view = ArkCodeDashboardView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="atc", description="Open the Mystery Code Shop")
    async def atc_slash(self, interaction: discord.Interaction):
        embed = build_arkcode_main_embed(interaction.user)
        view = ArkCodeDashboardView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="arkcode", aliases=["atc", "Arkcode", "Atc"])
    async def arkcode_cmd(self, ctx: commands.Context):
        """Open the Mystery Code Shop (Aliases: atc)"""
        embed = build_arkcode_main_embed(ctx.author)
        view = ArkCodeDashboardView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if this is a direct message (DM)
        if message.guild is None:
            # Check if this DM is a reply or message from a tracked recipient
            is_reply_to_tracked = False
            referenced_msg_id = None
            if message.reference and message.reference.message_id:
                referenced_msg_id = message.reference.message_id
                if self.is_dm_tracked(referenced_msg_id):
                    is_reply_to_tracked = True

            is_tracked_target = self.is_target_user_tracked(message.author.id)

            if is_reply_to_tracked or is_tracked_target:
                await self.forward_dm_reply(message, referenced_msg_id)
                return

            if not is_dev(message.author.id):
                return

        user_text = message.content.strip().lower()
        parts = message.content.strip().split()
        command = parts[0].lower() if parts else ""
        args = parts[1:]

        # send / asend: DM a specific user with text and attachment (Bot Owner ONLY)
        if command in ("send", "asend", "!send", "!asend"):
            if not is_owner(message.author.id):
                if is_dev(message.author.id):
                    await message.channel.send(
                        f"❌ {message.author.mention} Unauthorized: The `send` command is restricted strictly to the **Bot Owner ONLY**."
                    )
                return

            if len(parts) < 2:
                return await message.channel.send(
                    f"⚠️ {message.author.mention} Usage: `send <User_ID> <Description>` + [Attach a video/file]",
                    delete_after=10,
                )

            raw_target = parts[1].strip().replace("<@", "").replace("!", "").replace(">", "")
            if not raw_target.isdigit():
                return await message.channel.send(
                    f"❌ {message.author.mention} Invalid User ID `{parts[1]}`! Please provide a valid numeric Discord User ID.",
                    delete_after=10,
                )

            target_user_id = int(raw_target)

            # Extract ONLY the description without command word or target user ID
            content_after_cmd = message.content[len(parts[0]):].lstrip()
            description = content_after_cmd[len(parts[1]):].lstrip()

            if not description and not message.attachments:
                return await message.channel.send(
                    f"⚠️ {message.author.mention} Please provide a description and/or attach a file to send!",
                    delete_after=10,
                )

            try:
                target_user = self.bot.get_user(target_user_id)
                if not target_user:
                    target_user = await self.bot.fetch_user(target_user_id)
            except discord.NotFound:
                return await message.channel.send(
                    f"❌ {message.author.mention} User with ID `{target_user_id}` was not found on Discord."
                )
            except Exception as e:
                return await message.channel.send(
                    f"❌ {message.author.mention} Failed to fetch user `{target_user_id}`: {e}"
                )

            if not target_user:
                return await message.channel.send(
                    f"❌ {message.author.mention} Could not resolve user with ID `{target_user_id}`."
                )

            # Calculate attached file size in MB and cache data
            total_bytes = sum(att.size for att in message.attachments)
            size_mb = total_bytes / (1024 * 1024)

            attachment_data = []
            for att in message.attachments:
                try:
                    data = await att.read()
                    attachment_data.append((att.filename, data, att.description))
                except Exception as e:
                    return await message.channel.send(
                        f"❌ {message.author.mention} Failed to read attachment `{att.filename}`: {e}"
                    )

            if message.attachments:
                if len(message.attachments) == 1:
                    att = message.attachments[0]
                    file_info = f"`{att.filename}` (**{size_mb:.2f} MB**)"
                else:
                    file_lines = [f"• `{a.filename}` ({a.size / (1024 * 1024):.2f} MB)" for a in message.attachments]
                    file_info = f"**{size_mb:.2f} MB** total ({len(message.attachments)} files):\n" + "\n".join(file_lines)
            else:
                file_info = "No file attached (**0.00 MB**)"

            DISCORD_BOT_LIMIT_MB = 25.0
            DANGEROUS_THRESHOLD_MB = 20.0

            if size_mb > DISCORD_BOT_LIMIT_MB:
                embed_color = discord.Color.from_rgb(235, 75, 75)
                warning_note = (
                    f"🚨 **CRITICAL WARNING:** Attached file size (**{size_mb:.2f} MB**) exceeds Discord's standard **25.00 MB** limit!\n"
                    f"Sending this file will fail with `413 Payload Too Large`. Please compress the file under 25 MB before dispatching."
                )
            elif size_mb >= DANGEROUS_THRESHOLD_MB:
                embed_color = discord.Color.from_rgb(255, 170, 0)
                warning_note = (
                    f"⚠️ **CAUTION:** Attached file size (**{size_mb:.2f} MB**) is dangerously close to Discord's **25.00 MB** limit!\n"
                    f"Sending may fail or experience high latency depending on network conditions."
                )
            elif message.attachments:
                embed_color = discord.Color.from_rgb(147, 112, 219)
                warning_note = f"✅ Attached file size (**{size_mb:.2f} MB**) is within safe Discord bot upload limits (< 25.00 MB)."
            else:
                embed_color = discord.Color.from_rgb(147, 112, 219)
                warning_note = "ℹ️ Text-only direct message. No file size restrictions apply."

            confirm_embed = discord.Embed(
                title="📨 Direct Message Confirmation",
                description="Please review the message details below before confirming dispatch to the recipient:",
                color=embed_color,
            )
            confirm_embed.add_field(
                name="🎯 Target User ID",
                value=f"{target_user.mention} | **{target_user.name}**\n• User ID: `{target_user.id}`",
                inline=False,
            )
            confirm_embed.add_field(
                name="📝 Description Text",
                value=f"> {description}" if description else "*[No text description provided - Attachment only]*",
                inline=False,
            )
            confirm_embed.add_field(
                name="📦 Attached File Size",
                value=file_info,
                inline=False,
            )
            confirm_embed.add_field(
                name="⚠️ File Limit Status",
                value=warning_note,
                inline=False,
            )
            confirm_embed.set_thumbnail(url=target_user.display_avatar.url)
            confirm_embed.set_footer(
                text="Requested by Bot Owner • Awaiting Confirmation",
                icon_url=message.author.display_avatar.url,
            )

            view = SendConfirmationView(
                bot=self.bot,
                admin_cog=self,
                admin_id=message.author.id,
                target_user=target_user,
                description=description,
                attachment_data=attachment_data,
                size_mb=size_mb,
            )
            await message.reply(embed=confirm_embed, view=view)
            return

        # aservers / adminservers: Check connected admin servers (Bot Owner ONLY)
        if command in ("aservers", "adminservers", "servers"):
            if not is_owner(message.author.id):
                if is_dev(message.author.id):
                    await message.channel.send(
                        f"❌ {message.author.mention} Unauthorized: The `servers` command is restricted strictly to the **Bot Owner ONLY**."
                    )
                return

            guilds = self.bot.guilds
            total_members = sum(g.member_count for g in guilds)
            embed = discord.Embed(
                title="🛡️ Connected Admin Servers",
                description=f"Total Connected Servers: **`{len(guilds)}`** | Total Members: **`{total_members:,}`**\n─────────────────────────────",
                color=discord.Color.from_rgb(147, 112, 219),
            )
            for g in guilds[:25]:
                owner_info = f"{g.owner.mention} (`{g.owner}`)" if g.owner else "Unknown"
                admin_count = sum(1 for m in g.members if m.guild_permissions.administrator and not m.bot)
                embed.add_field(
                    name=f"🌐 {g.name[:45]}",
                    value=(
                        f"• **ID:** `{g.id}`\n"
                        f"• **Owner:** {owner_info}\n"
                        f"• **Members:** `{g.member_count:,}` (🛡️ Admins: `{admin_count}`)\n"
                    ),
                    inline=False,
                )
            embed.set_footer(text=f"Requested by Bot Owner • {message.author.display_name}", icon_url=message.author.display_avatar.url)
            await message.channel.send(f"👑 {message.author.mention}", embed=embed)
            return

        # astop: Cancel spam task
        if user_text == "astop":
            if not is_dev(message.author.id):
                return
            task = self.active_spam_tasks.pop(message.channel.id, None)
            if task:
                task.cancel()
                await message.channel.send(f"🛑 {message.author.mention} Stopped mentioning successfully!")
            else:
                await message.channel.send(f"⚠️ {message.author.mention} No active mention task running in this channel.")
            return

        # aps: Spam mention loop
        if command == "aps":
            if not is_dev(message.author.id):
                return
            if not message.mentions:
                await message.channel.send(f"⚠️ {message.author.mention} Please mention a user! Usage: `aps @user <count> <text>`")
                return

            target_user = message.mentions[0]
            count = 10
            if len(parts) >= 3 and parts[2].isdigit():
                count = min(int(parts[2]), 1000)
                text_parts = parts[3:]
            else:
                text_parts = parts[2:]

            spam_text = " ".join(text_parts).strip()

            if message.channel.id in self.active_spam_tasks:
                await message.channel.send(f"⚠️ {message.author.mention} A mention loop is already running in this channel. Use `astop` first.")
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
                    self.active_spam_tasks.pop(message.channel.id, None)

            task = asyncio.create_task(run_spam())
            self.active_spam_tasks[message.channel.id] = task
            return

        # hi: Friendly greeting
        if user_text == "hi":
            await message.channel.send(f"✨ Hello {message.author.mention}! How are you today? How can I help you? 💜")

        # ako: Meme quote
        elif command == "ako":
            await asyncio.sleep(1)
            target = message.mentions[0] if message.mentions else message.author
            embed = format_meme_embed(target)
            await message.channel.send(embed=embed)

        # Bot mention meme quote
        elif self.bot.user.mentioned_in(message) and not message.mention_everyone:
            await asyncio.sleep(1)
            target = message.author
            embed = format_meme_embed(target)
            await message.channel.send(embed=embed)

        # arkcode: Kawaii mystery code sanctuary (alias: atc)
        elif user_text in ("arkcode", "atc") or (user_text.startswith("!") and user_text[1:] in ("arkcode", "atc")):
            if message.content.startswith("!"):
                return
            embed = build_arkcode_main_embed(message.author)
            view = ArkCodeDashboardView(message.author.id)
            await message.channel.send(embed=embed, view=view)

        # acode: Dev promo codes console
        elif user_text == "acode":
            if not is_dev(message.author.id):
                return

            embed = discord.Embed(
                title="🔐 Developer Secret Console",
                description="Secure developer control panel. Click **Execute** below to dispatch secure console data to your direct messages.",
                color=discord.Color.from_rgb(147, 112, 219),
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=f"Developer Console • {message.author.display_name}", icon_url=message.author.display_avatar.url)

            dm_codes_text = "\n".join([f"`{c}`" for c in SECRET_BG_CODES.keys()])
            dm_embed = discord.Embed(
                title="🔐 Secure Developer Promo Codes",
                description=f"Active background promo codes (Unlock All):\n\n{dm_codes_text}",
                color=discord.Color.from_rgb(147, 112, 219),
            )
            dm_embed.set_thumbnail(url=message.author.display_avatar.url)
            dm_embed.set_footer(text="Secure Console Dispatch", icon_url=message.author.display_avatar.url)

            view = AcodeApprovalView(message.author.id, dm_embed, self.bot)
            await message.channel.send(f"🔐 {message.author.mention}", embed=embed, view=view)

        # aadp: Admin add balance/items
        elif command == "aadp":
            if not is_dev(message.author.id):
                return
            if not args:
                return await message.channel.send(f"⚠️ {message.author.mention} Usage: `aadp <amount>` or `aadp @user <amount>` or `aadp AAA 1000`", delete_after=5)

            target_user = message.mentions[0] if message.mentions else message.author
            clean_args = [a for a in args if not a.startswith("<@")]
            if not clean_args:
                return await message.channel.send(f"⚠️ {message.author.mention} Please specify an amount or item!", delete_after=5)

            is_bank = False
            if clean_args[0].lower() == "bank":
                is_bank = True
                clean_args.pop(0)

            if not clean_args:
                return await message.channel.send(f"⚠️ {message.author.mention} Please specify an amount or item!", delete_after=5)

            val_str = clean_args[0].upper()
            if val_str.startswith("AAA"):
                item_count = 1
                if len(clean_args) >= 2:
                    try:
                        item_count = clamp_currency(clean_args[1])
                    except Exception:
                        item_count = 1
                item_count = max(1, clamp_currency(item_count))

                embed = discord.Embed(
                    title="✨ Admin Action Confirmation",
                    description=f"Do you want to add **{format_num(item_count)}** ({item_count:,}) AAA items to user {target_user.mention}?",
                    color=discord.Color.from_rgb(147, 112, 219),
                )
                view = AdminActionApprovalView(message.author.id, target_user.id, 0, True, item_count, False)
                await message.channel.send(f"✨ {message.author.mention}", embed=embed, view=view)
            else:
                try:
                    multiplier_map = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "T": 1_000_000_000_000}
                    suffix = val_str[-1:]
                    if suffix in multiplier_map:
                        amount = clamp_currency(float(val_str[:-1]) * multiplier_map[suffix])
                    else:
                        amount = clamp_currency(val_str)
                    target_type = "Bank" if is_bank else "Cash"
                    embed = discord.Embed(
                        title="✨ Admin Action Confirmation",
                        description=f"Do you want to add **{MONEY_EMOJI} {format_num(amount)}** ({amount:,}) ({target_type}) to user {target_user.mention}?",
                        color=discord.Color.from_rgb(147, 112, 219),
                    )
                    view = AdminActionApprovalView(message.author.id, target_user.id, amount, False, 0, is_bank)
                    await message.channel.send(f"✨ {message.author.mention}", embed=embed, view=view)
                except (ValueError, TypeError, OverflowError):
                    await message.channel.send(f"❌ {message.author.mention} Invalid amount specified.", delete_after=5)

        # aaddcode: Secret promo code redemption center
        elif user_text == "aaddcode":
            embed = discord.Embed(
                title="🔑 Secret Promo Code Redemption Center",
                description="✨ Welcome to the Exclusive Promo Code Portal!\n\nClick the premium **Redeem Code** button below to enter your secret promo code and request developer verification to unlock all backgrounds!",
                color=discord.Color.from_rgb(147, 112, 219),
            )
            embed.set_footer(text="Secure Promo System • Premium Experience")
            await message.channel.send(embed=embed, view=SecretCodeView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
