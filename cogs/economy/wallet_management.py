import math
from typing import TYPE_CHECKING

import math
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from helpers.time_inputs import human_timedelta
from ._base import EconomyBase
from .helper_classes import Wallet
from .helper_functions import require_setup, refresh

if TYPE_CHECKING:
    from helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


class WalletManagement(EconomyBase):
    @require_setup()
    @refresh()
    @commands.command(name="balance", aliases=["bal", "money", "cash", 'wallet'])
    async def balance(self, ctx: CustomContext, *, user: discord.User = None):
        """Shows your current balance."""
        if user:
            wallet = await self.bot.get_wallet(user)
            return await ctx.send(f"{self.coin_emoji} **{wallet.user}** has **{wallet.balance} {self.coin_name}**.")
        await ctx.send(f"{self.coin_emoji} **You** have **{ctx.wallet.balance} {self.coin_name}**.")

    @require_setup()
    @refresh()
    @commands.command(name="pay", aliases=["give", "transfer"])
    async def pay(self, ctx: CustomContext, user: discord.User, amount: int):
        """Pay another user some money."""
        async with ctx.wallet as wallet:
            await wallet.transfer_money(user, amount)
            await ctx.send(f"{self.coin_emoji} **You** gave **{amount} {self.coin_name}** to **{user}**.")

    @commands.group(
        name='eco',
        aliases=['economy'],
        invoke_without_command=True,
        usage='',
        brief='Economy management/information commands',
    )
    async def economy(self, ctx: CustomContext, x=None):
        """The `eco` command group. **These are mostly for statistics, information and setup of the economy.** See other economy-related, located in the `Economy` category, by running `%PRE%help Economy`."""
        if not x:
            await ctx.send_help(ctx.command)
        else:
            raise commands.BadArgument(f'Unknown subcommand "{x[0:50]}".')

    @economy.command(name='start')
    async def eco_start(self, ctx: CustomContext):
        """Creates a wallet for the user.
        (Aka opts-in to the economy commands.)"""
        await Wallet.create(ctx.bot, ctx.author)
        await ctx.send(
            f"{self.coin_emoji} **{ctx.me.name}** gifts you this **👛 Duck Wallet** with **200 {self.coin_emoji} {self.coin_name}** and a **📦 Storage box**."
        )

    @require_setup()
    @refresh()
    @economy.command(name='stop')
    async def eco_stop(self, ctx: CustomContext):
        """Returns your wallet to the bot.
        (aka opts-out of the economy commands.)"""
        async with ctx.wallet:
            if ctx.wallet.balance < 200:
                raise commands.BadArgument(f"❗ Sorry but opting out costs **200 {self.coin_name}**.")
            prompt = await ctx.confirm(
                f"**__Are you sure you want to do that?__**"
                f"\n\n{ctx.bot.constants.ARROW} This will:"
                f"\n- Return your **👛 Duck Wallet** the me."
                f"\n- Throw away your **📦 Storage Box**."
                f"\n\n{ctx.bot.constants.ARROW} This will **not**:"
                f"\n- Reset your **⏲ Cooldown**"
                "\n\n**This action cannot be undone.**",
                delete_after_confirm=True,
                buttons=(('✋', 'Return wallet', discord.ButtonStyle.gray), ('🗑', None, discord.ButtonStyle.red)),
            )
            if not prompt:
                return
            await ctx.wallet.delete()
            await ctx.send(
                f"{self.coin_emoji} **{ctx.me.name}** took your **👛 Duck Wallet** and thew away your **📦 Storage Box**."
            )

    @require_setup()
    @economy.command(name='cooldowns', aliases=['cd', 'cooldown'])
    async def eco_cd(self, ctx: CustomContext):
        """Shows the cooldowns for the economy commands."""
        async with ctx.wallet as wallet:
            embed = discord.Embed(title="Your cooldowns")
            embed.add_field(
                name=f"{ctx.tick(wallet.can_work)} Work",
                inline=False,
                value=f"Next available: {discord.utils.format_dt(wallet.next_work, style='R')}"
                f"\n(in {human_timedelta(wallet.next_work, accuracy=2)})"
                if not wallet.can_work
                else "Available: Now\n(every 10 minutes)",
            )
            embed.add_field(
                name=f"{ctx.tick(wallet.can_daily)} Daily",
                inline=False,
                value=f"Next available: {discord.utils.format_dt(wallet.next_daily, style='R')}"
                f"\n(in {human_timedelta(wallet.next_daily, accuracy=2)})"
                if not wallet.can_daily
                else "Available: Now\n(every 24 hours)",
            )
            embed.add_field(
                name=f"{ctx.tick(wallet.can_weekly)} Weekly",
                inline=False,
                value=f"Next available: {discord.utils.format_dt(wallet.next_weekly, style='R')}"
                f"\n(in {human_timedelta(wallet.next_weekly, accuracy=2)})"
                if not wallet.can_weekly
                else "Available: Now\n(every 7 days)",
            )
            embed.add_field(
                name=f"{ctx.tick(wallet.can_monthly)} Monthly",
                inline=False,
                value=f"Next available: {discord.utils.format_dt(wallet.next_monthly, style='R')}"
                f"\n(in {human_timedelta(wallet.next_monthly, accuracy=2)})"
                if not wallet.can_monthly
                else "Available: Now\n(every 30 days)",
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, footer=False)

    @economy.command(name='leaderboard', aliases=['lb', 'top'])
    async def eco_leaderboard(self, ctx: CustomContext, page: int = 1):
        """Shows the top richest users in the economy."""
        if page < 1:
            raise commands.BadArgument("Page must be greater than 0.")
        page -= 1
        count = await ctx.bot.db.fetchval("SELECT COUNT(*) FROM economy")
        if count == 0:
            raise commands.BadArgument("❗ There are no users in the economy yet.")
        users = await ctx.bot.db.fetch(
            "SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 10 OFFSET $1", page * 10
        )
        if not users:
            raise commands.BadArgument("❗ That page does not exist.")
        embed = discord.Embed(title=f"Top {count} richest users (page {page+1}/{math.ceil(count / 10)})")
        leaderboard = []
        for number, entry in enumerate(users, start=page * 10 + 1):
            user = discord.utils.escape_markdown(str(ctx.bot.get_user(entry.get('user_id', 0)) or 'Unknown User'))
            leaderboard.append(f"`{number}`) **{user}** - {entry.get('balance')} {self.coin_emoji}")
        embed.description = "\n".join(leaderboard)
        max_page = page * 10 + 10
        max_page = max_page if max_page < count else count
        embed.set_footer(text=f"Showing users {page * 10 + 1}-{max_page} of {count}.")
        await ctx.send(embed=embed)
