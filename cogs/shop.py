import asyncio
import traceback

import discord
from discord.ext import commands

from cogs import (
    AVATAR_BORDERS,
    BACKGROUNDS,
    BACKGROUND_AAA_PRICE,
    BACKGROUND_COIN_PRICE,
    DEFAULT_BG,
    DEFAULT_BORDER,
    URL_DEVELOPER,
    URL_FAQ,
    URL_SUPPORT,
    border_prices,
    buy_avatar_border,
    buy_background,
    equip_avatar_border,
    equip_background,
    format_num,
    get_border_state,
    get_shop_state,
    get_user_avatar_border,
    get_user_background_filename,
    get_user_data,
    is_dev,
)
from cogs.profile import generate_profile_card

SHOP_COLOR = discord.Color.from_rgb(147, 112, 219)

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


def _price_line(kind: str, code: str) -> str:
    """Exact price text. E.g., '4,000,000 Coins or 30 AAA'. Free default item shows 'Free'."""
    if kind == "bg":
        if code == DEFAULT_BG:
            return "**Free**"
        return f"**{BACKGROUND_COIN_PRICE:,} Coins** or **{BACKGROUND_AAA_PRICE} AAA**"
    coins, aaa = border_prices(code)
    return f"**{coins:,} Coins** or **{aaa} AAA**"


def _item_state(user_id: int, kind: str, code: str):
    """Return whether the user owns or has equipped an item."""
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


def _wallet(user_id: int):
    data = get_user_data(user_id)
    return data[0], data[6]  # (coins, AAA)


def _shop_result_embed(success: bool, msg: str) -> discord.Embed:
    return discord.Embed(
        title="✅ Done" if success else "❌ Couldn't complete that",
        description=msg,
        color=discord.Color.green() if success else discord.Color.red(),
    )


def _dropdown_options(user_id: int, kind: str):
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
    return options[:25]


class ShopDropdown(discord.ui.Select):
    def __init__(self, user_id: int, kind: str):
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
        await interaction.response.defer()
        await _show_panel(interaction, self.kind, self.values[0])


class MainShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.add_item(ShopDropdown(user_id, "bg"))
        self.add_item(ShopDropdown(user_id, "border"))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="💻 Developer", url=URL_DEVELOPER, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="🛠️ Support", url=URL_SUPPORT, row=2))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="❓ FAQ", url=URL_FAQ, row=2))


def create_main_shop_embed(user_id: int):
    coins, aaa = _wallet(user_id)
    embed = discord.Embed(
        title="🛍️ Profile Shop",
        description=f"🔷 **{format_num(coins)}** ({coins:,}) Coins\n💎 **{format_num(aaa)}** AAA\n\nPick an item below to preview it.",
        color=SHOP_COLOR,
    )
    embed.set_footer(text="See your result with aup / ap")
    return embed, MainShopView(user_id)


async def _create_shop_preview(user: discord.User, guild: discord.Guild, bg_code=None, border_code=None) -> discord.File:
    """Render the exact profile card being previewed entirely in-memory."""
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

    buf = await asyncio.to_thread(
        generate_profile_card,
        avatar_bytes,
        user.display_name,
        level,
        chat_xp,
        voice_xp,
        aaa_count,
        guild.name if guild else "Server",
        server_icon_bytes,
        None,  # Returns BytesIO
        bg_filename,
        ring_style,
    )
    return discord.File(buf, filename="profile-preview.png")


def _panel_embed(user_id: int, kind: str, code: str, notice: str = None) -> discord.Embed:
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
    embed.set_footer(text=f"🔷 {format_num(coins)} ({coins:,})  •  💎 {format_num(aaa)} ({aaa:,})")
    return embed


class ItemPanelView(discord.ui.View):
    """Buy / Equip / Default / Back controls."""

    def __init__(self, user_id: int, kind: str, code: str):
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


class PaymentView(discord.ui.View):
    """Ephemeral two-button picker: Coins or AAA."""

    def __init__(self, user_id: int, kind: str, code: str, parent_message: discord.Message):
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

    async def _purchase(self, interaction: discord.Interaction, method: str):
        if self.kind == "bg":
            ok, msg = buy_background(self.user_id, self.code, method)
        else:
            ok, msg = buy_avatar_border(self.user_id, self.code, method)
        await interaction.response.edit_message(content=None, embed=_shop_result_embed(ok, msg), view=None)
        if ok and self.parent_message is not None:
            try:
                param = {"bg_code": self.code} if self.kind == "bg" else {"border_code": self.code}
                file = await _create_shop_preview(interaction.user, interaction.guild, **param)
                await self.parent_message.edit(
                    embed=_panel_embed(self.user_id, self.kind, self.code, "✅ Purchased and equipped!"),
                    view=ItemPanelView(self.user_id, self.kind, self.code),
                    attachments=[file],
                )
            except (discord.HTTPException, OSError):
                traceback.print_exc()

    @discord.ui.button(label="Coins", emoji="🔷", style=discord.ButtonStyle.success)
    async def coins_button(self, interaction: discord.Interaction, _button):
        await self._purchase(interaction, "coins")

    @discord.ui.button(label="AAA", emoji="💎", style=discord.ButtonStyle.primary)
    async def aaa_button(self, interaction: discord.Interaction, _button):
        await self._purchase(interaction, "aaa")


async def _show_panel(interaction: discord.Interaction, kind: str, code: str, notice: str = None):
    try:
        param = {"bg_code": code} if kind == "bg" else {"border_code": code}
        file = await _create_shop_preview(interaction.user, interaction.guild, **param)
    except Exception:
        traceback.print_exc()
        return await interaction.followup.send("Sorry, the preview could not be generated.", ephemeral=True)

    await interaction.edit_original_response(
        embed=_panel_embed(interaction.user.id, kind, code, notice),
        view=ItemPanelView(interaction.user.id, kind, code),
        attachments=[file],
    )


class Shop(commands.Cog):
    """Background and avatar border shopping, equipping, and live previews."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None and not is_dev(message.author.id):
            return

        user_text = message.content.strip().lower()
        if user_text in ("ashop", "ash"):
            embed, view = create_main_shop_embed(message.author.id)
            await message.channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
