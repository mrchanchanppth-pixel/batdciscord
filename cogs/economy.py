import re

import discord
from discord.ext import commands

from cogs import (
    DAILY_COOLDOWN,
    DAILY_REWARD,
    MAX_CURRENCY_CAP,
    MONEY_EMOJI,
    TRANSFER_HOURLY_LIMIT,
    WEEKLY_COOLDOWN,
    WEEKLY_REWARD,
    BalDirectShopView,
    StandardLinksView,
    claim_reward,
    deposit_to_bank,
    format_days_hours,
    format_hours_minutes,
    format_num,
    get_hourly_transfer_total,
    get_user_data,
    is_dev,
    parse_amount,
    perform_robbery,
    transfer_coins,
    withdraw_from_bank,
)
from cogs.admin import CallableBool


def _resolve_rob_target(message: discord.Message, args: list):
    """Prefer the mention or user ID written right after the command; fall back to the first mention."""
    if args:
        match = re.fullmatch(r"<@!?(\d+)>", args[0])
        if match:
            wanted = int(match.group(1))
            for user in message.mentions:
                if user.id == wanted:
                    return user
        elif args[0].isdigit() and message.guild:
            member = message.guild.get_member(int(args[0]))
            if member:
                return member
    return message.mentions[0] if message.mentions else None


async def _cmd_rob(message: discord.Message, args: list):
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
            description=(f"{thief.mention} stole **{MONEY_EMOJI} {format_num(result['amount'])}** "
                         f"({result['percent']}%) from {target.mention}!"),
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title="🚨 Caught!",
            description=(f"{thief.mention} got caught and paid **{MONEY_EMOJI} {format_num(result['amount'])}** "
                         f"({result['percent']}% of their cash) to {target.mention} as compensation."),
            color=discord.Color.red(),
        )
    embed.set_thumbnail(url=thief.display_avatar.url)
    embed.set_footer(text=f"Your cash: {format_num(result['thief_cash'])}  •  Bank money can't be robbed")
    await message.channel.send(embed=embed)


class PayConfirmationView(discord.ui.View):
    """Interactive confirmation dialog for coin transfers."""

    def __init__(
        self,
        sender_id: int,
        target_user: discord.User | discord.Member,
        amount: int,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.sender_id = sender_id
        self.target_user = target_user
        self.amount = amount
        self._is_action_done = False

    @property
    def is_finished(self) -> CallableBool:
        done = getattr(self, "_is_action_done", False) or super().is_finished()
        return CallableBool(done)

    @is_finished.setter
    def is_finished(self, value):
        self._is_action_done = bool(value)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.sender_id:
            await interaction.response.send_message(
                f"❌ {interaction.user.mention} This payment confirmation belongs to someone else.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Accept", emoji="✅", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_finished:
            return
        self.is_finished = True
        self.stop()

        success, msg, new_sender_bal, _new_target_bal = transfer_coins(
            self.sender_id, self.target_user.id, self.amount
        )
        if success:
            hourly_total = get_hourly_transfer_total(self.sender_id)
            embed = discord.Embed(
                title="💸 Transfer Successful!",
                description=(
                    f"✨ Successfully transferred **{MONEY_EMOJI} {format_num(self.amount)}** ({self.amount:,}) coins to {self.target_user.mention}!\n\n"
                    f"• 💳 **Your New Cash:** `{MONEY_EMOJI} {format_num(new_sender_bal)}` ({new_sender_bal:,})\n"
                    f"• ⏳ **Hourly Sent:** `{format_num(hourly_total)} / 10M` (Resets rolling 60m)"
                ),
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            embed.set_footer(text=f"Sent by {interaction.user.display_name}")
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="❌ Transfer Failed",
                description=msg,
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_finished:
            return
        self.is_finished = True
        self.stop()

        embed = discord.Embed(
            title="🛑 Transfer Cancelled",
            description=f"Transaction of **{MONEY_EMOJI} {format_num(self.amount)}** ({self.amount:,}) coins to {self.target_user.mention} was cancelled.",
            color=discord.Color.from_rgb(108, 117, 125),
        )
        embed.set_footer(text="Cancelled by sender")
        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def on_timeout(self):
        if not self.is_finished:
            self.is_finished = True
            for child in self.children:
                child.disabled = True


async def _process_pay_command(channel, author: discord.Member | discord.User, args: list[str], guild: discord.Guild | None):
    if not args:
        return await channel.send(
            f"⚠️ {author.mention} Usage: `!Apay @user <amount>` or `!Apay <amount> @user`\n"
            f"Example: `!Apay @friend 1m` or `!Apay 500k @friend`",
            delete_after=7,
        )

    target = None
    amount = None

    # Check mentions first
    mention_match = None
    for a in args:
        m = re.fullmatch(r"<@!?(\d+)>", a)
        if m:
            mention_match = (a, int(m.group(1)))
            break

    if mention_match:
        mention_token, target_id = mention_match
        target = guild.get_member(target_id) if guild else None
        if not target and hasattr(channel, "guild") and channel.guild:
            target = channel.guild.get_member(target_id)
        # Find amount in remaining args
        rem_args = [a for a in args if a != mention_token]
        for a in rem_args:
            parsed = parse_amount(a)
            if parsed is not None:
                amount = parsed
                break
    else:
        # No mention tag found: inspect tokens [arg0, arg1]
        amt0 = parse_amount(args[0])
        amt1 = parse_amount(args[1]) if len(args) > 1 else None

        if amt0 is not None and len(args) > 1:
            # Format: !Apay 1m @user or !Apay 1m 123456789
            amount = amt0
            target_token = args[1]
            if target_token.isdigit() and guild:
                target = guild.get_member(int(target_token))
            elif guild:
                target = discord.utils.find(
                    lambda m: m.name.lower() == target_token.lower() or m.display_name.lower() == target_token.lower(),
                    guild.members,
                )
        elif amt1 is not None:
            # Format: !Apay @user 1m or !Apay 123456789 1m
            amount = amt1
            target_token = args[0]
            if target_token.isdigit() and guild:
                target = guild.get_member(int(target_token))
            elif guild:
                target = discord.utils.find(
                    lambda m: m.name.lower() == target_token.lower() or m.display_name.lower() == target_token.lower(),
                    guild.members,
                )

    if target is None:
        return await channel.send(
            f"❌ {author.mention} Could not find target user! Please mention them or use their ID (e.g. `!Apay @user 1m`).",
            delete_after=6,
        )

    if amount is None or amount <= 0:
        return await channel.send(
            f"❌ {author.mention} Please enter a valid transfer amount (e.g. `1000000`, `1k`, `1m`, `1b`).",
            delete_after=6,
        )

    if target.id == author.id:
        return await channel.send(f"❌ {author.mention} You cannot transfer coins to yourself!", delete_after=5)

    if getattr(target, "bot", False):
        return await channel.send(f"❌ {author.mention} You cannot transfer coins to a bot!", delete_after=5)

    # Check sender balance
    bal_data = get_user_data(author.id)
    sender_bal = bal_data[0]
    if sender_bal < amount:
        return await channel.send(
            embed=discord.Embed(
                title="❌ Insufficient Cash on Hand",
                description=(
                    f"{author.mention} You need **{MONEY_EMOJI} {format_num(amount)}** ({amount:,}) cash on hand, "
                    f"but you only have **{MONEY_EMOJI} {format_num(sender_bal)}** ({sender_bal:,}) cash!\n\n"
                    "✨ *Tip: If your coins are in your bank, use `ajenh <amount>` to withdraw first.*"
                ),
                color=discord.Color.red(),
            ),
            delete_after=8,
        )

    # Check hourly limit
    sent_last_hour = get_hourly_transfer_total(author.id)
    if sent_last_hour + amount > TRANSFER_HOURLY_LIMIT:
        remaining_quota = max(0, TRANSFER_HOURLY_LIMIT - sent_last_hour)
        return await channel.send(
            embed=discord.Embed(
                title="⚠️ Hourly Transfer Limit Exceeded",
                description=(
                    f"{author.mention} You have already transferred **{MONEY_EMOJI} {format_num(sent_last_hour)}** ({sent_last_hour:,}) coins in the last 60 minutes.\n\n"
                    f"• **Hourly Limit:** `10,000,000 (10M)` coins\n"
                    f"• **Remaining Limit:** **{MONEY_EMOJI} {format_num(remaining_quota)}** ({remaining_quota:,}) coins\n\n"
                    "Please wait for your rolling 60-minute window to reset before sending more coins!"
                ),
                color=discord.Color.red(),
            )
        )

    # Prompt with Confirmation View
    confirm_embed = discord.Embed(
        title="💸 Coin Transfer Confirmation",
        description=(
            f"Are you sure you want to transfer coins?\n\n"
            f"• 🎯 **Recipient:** {target.mention} (`{target.display_name}`)\n"
            f"• 💰 **Amount:** **{MONEY_EMOJI} {format_num(amount)}** ({amount:,}) coins\n"
            f"• ⏳ **Hourly Quota After Transfer:** `{format_num(sent_last_hour + amount)} / 10M`\n\n"
            "Click ✅ **Accept** to finalize the transaction or ❌ **Cancel** to abort."
        ),
        color=discord.Color.from_rgb(147, 112, 219),
    )
    confirm_embed.set_thumbnail(url=target.display_avatar.url)
    confirm_embed.set_footer(text=f"Requested by {author.display_name} • Confirmation expires in 60s")

    view = PayConfirmationView(author.id, target, amount)
    await channel.send(f"✨ {author.mention}", embed=confirm_embed, view=view)


class Economy(commands.Cog):
    """Coins balance, banking operations, reward claims, member robberies, and coin transfers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    async def _send_balance_embed(user: discord.User | discord.Member, channel: discord.abc.Messageable):
        balance, bank, _xp, _level, _chat_xp, _voice_xp, aa_count = get_user_data(user.id)
        embed_description = (
            f"**Coins :** `{format_num(balance)}` {MONEY_EMOJI}\n"
            f"**Bank :** `{format_num(bank)}` 🏦\n"
            f"**AAA :** `{format_num(aa_count)}` 💎\n"
            f"───────────────\n"
            f"✨ **Total Wealth:** `{format_num(balance + bank)}` Coins"
        )
        embed = discord.Embed(
            title=f"🌸 • | {user.display_name}'s Balance",
            description=embed_description,
            color=discord.Color.from_rgb(147, 112, 219)
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Exact Balance: {balance:,} cash | {bank:,} bank")
        await channel.send(embed=embed, view=BalDirectShopView())

    @commands.command(name="abal", aliases=['Abal', 'Abank', 'Abk'])
    async def cmd_abal(self, ctx: commands.Context):
        """Check your cash balance, bank savings, and AAA items. (Aliases: Abal, Abank, Abk)"""
        await self._send_balance_embed(ctx.author, ctx.channel)

    @commands.command(name="pay", aliases=['Apay', 'Apy', 'apay', 'apy'])
    async def cmd_pay(self, ctx: commands.Context, *args):
        """Transfer coins to another user. Usage: !Apay @user 1m or !Apay 1m @user"""
        await _process_pay_command(ctx.channel, ctx.author, list(args), ctx.guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None and not is_dev(message.author.id):
            return

        user_text = message.content.strip().lower()
        parts = message.content.strip().split()
        command = parts[0].lower() if parts else ""
        args = parts[1:]

        # Prefixed commands handled by discord.py's command processor
        if message.content.startswith("!"):
            clean_cmd = command[1:]
            if clean_cmd in ("abal", "abank", "abk", "pay", "apay", "apy"):
                return

        # Robbery command: aoy or aoyyg
        if command in ("aoy", "aoyyg") or (command.startswith("!") and command[1:] in ("aoy", "aoyyg")):
            await _cmd_rob(message, args)
            return

        # Balance check: abal, abank, abk (when typed without "!")
        if user_text in ("abal", "abank", "abk"):
            await self._send_balance_embed(message.author, message.channel)
            return

        # Pay command: pay, apay, apy (when typed without "!")
        if command in ("pay", "apay", "apy"):
            await _process_pay_command(message.channel, message.author, args, message.guild)
            return

        # Deposit: ajol <amount|all>
        elif command in ("ajol", "!ajol"):
            if not args:
                return await message.channel.send("⚠️ Usage: `ajol <amount>` or `ajol all`", delete_after=5)

            amt_arg = args[0].lower()
            try:
                success, result_val, msg = deposit_to_bank(message.author.id, amt_arg)
            except ValueError:
                return await message.channel.send("⚠️ Please enter a valid number or `all`!", delete_after=5)

            if success:
                embed = discord.Embed(
                    title="🏦 Bank Deposit Successful",
                    description=f"✅ Successfully deposited **{MONEY_EMOJI} {format_num(result_val)}** into your bank account!",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Amount: {result_val:,} coins")
            else:
                embed = discord.Embed(
                    title="❌ Deposit Failed",
                    description=f"Reason: **{msg}**",
                    color=discord.Color.red()
                )
            await message.channel.send(embed=embed)

        # Withdraw: ajenh <amount|all>
        elif command in ("ajenh", "!ajenh"):
            if not args:
                return await message.channel.send("⚠️ Usage: `ajenh <amount>` or `ajenh all`", delete_after=5)

            amt_arg = args[0].lower()
            try:
                success, result_val, msg = withdraw_from_bank(message.author.id, amt_arg)
            except ValueError:
                return await message.channel.send("⚠️ Please enter a valid number or `all`!", delete_after=5)

            if success:
                embed = discord.Embed(
                    title="🏧 Bank Withdrawal Successful",
                    description=f"✅ Successfully withdrew **{MONEY_EMOJI} {format_num(result_val)}** from your bank account!",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Amount: {result_val:,} coins")
            else:
                embed = discord.Embed(
                    title="❌ Withdrawal Failed",
                    description=f"Reason: **{msg}**",
                    color=discord.Color.red()
                )
            await message.channel.send(embed=embed)

        # Daily reward: ad
        elif user_text in ("ad", "!ad"):
            success, result = claim_reward(message.author.id, "last_daily", DAILY_REWARD, DAILY_COOLDOWN)
            if success:
                embed = discord.Embed(
                    title="🎁 Daily Reward Claimed",
                    description=f"You successfully claimed your daily reward of **{MONEY_EMOJI} {format_num(DAILY_REWARD)}**!\n\nNew Cash Balance: **{MONEY_EMOJI} {format_num(result)}**",
                    color=discord.Color.green(),
                )
                embed.set_footer(text=f"Reward: {DAILY_REWARD:,} coins")
            else:
                embed = discord.Embed(
                    title="⏳ Daily Cooldown",
                    description=f"You have already claimed your daily reward!\n\nPlease wait **{format_hours_minutes(result)}** before claiming again.",
                    color=discord.Color.gold(),
                )
            await message.channel.send(embed=embed, view=StandardLinksView())

        # Weekly reward: aw
        elif user_text in ("aw", "!aw"):
            success, result = claim_reward(message.author.id, "last_weekly", WEEKLY_REWARD, WEEKLY_COOLDOWN)
            if success:
                embed = discord.Embed(
                    title="🎁 Weekly Reward Claimed",
                    description=f"You successfully claimed your weekly reward of **{MONEY_EMOJI} {format_num(WEEKLY_REWARD)}**!\n\nNew Cash Balance: **{MONEY_EMOJI} {format_num(result)}**",
                    color=discord.Color.green(),
                )
                embed.set_footer(text=f"Reward: {WEEKLY_REWARD:,} coins")
            else:
                embed = discord.Embed(
                    title="⏳ Weekly Cooldown",
                    description=f"You have already claimed your weekly reward!\n\nPlease wait **{format_days_hours(result)}** before claiming again.",
                    color=discord.Color.gold(),
                )
            await message.channel.send(embed=embed, view=StandardLinksView())


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
