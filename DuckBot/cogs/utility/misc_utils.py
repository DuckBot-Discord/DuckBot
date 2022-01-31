import typing

import discord
import tabulate
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from DuckBot.helpers import time_inputs
from ._base import UtilityBase


class MiscUtils(UtilityBase):

    @commands.command(aliases=['uuid'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def minecraft_uuid(self, ctx: CustomContext, *, username: str) \
            -> typing.Optional[discord.Message]:
        """ Fetches the UUID of a minecraft user from the Mojang API, and avatar from craftavatar.com """
        argument = username
        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
            if cs.status == 204:
                raise commands.BadArgument('That is not a valid Minecraft UUID!')
            elif cs.status != 200:
                raise commands.BadArgument('Something went wrong...')
            res = await cs.json()
            user = res["name"]
            uuid = res["id"]
            embed = discord.Embed(description=f"**UUID:** `{uuid}`")
            embed.set_author(icon_url=f'https://crafatar.com/avatars/{uuid}?size=128&overlay=true', name=user)
            return await ctx.send(embed=embed)

    @commands.command(name="in")
    async def _in_command(self, ctx, *, relative_time: time_inputs.ShortTime):
        """
        Shows a time in everyone's time-zone
          note that: `relative_time` must be a short time!
        for example: 1d, 5h, 3m or 25s, or a combination of those, like 3h5m25s (without spaces between these times)
        """

        await ctx.send(f"{discord.utils.format_dt(relative_time.dt, style='F')} "
                       f"({discord.utils.format_dt(relative_time.dt, style='R')})")

    @commands.command(aliases=['perms'], usage='[target] [channel]')
    @commands.guild_only()
    async def permissions(self, ctx: CustomContext,
                          target: typing.Optional[discord.Member],
                          channel: typing.Optional[discord.abc.GuildChannel],
                          _target: typing.Optional[discord.Member]):
        """
        Displays a user's server permissions, and their channel-specific overwrites.
        By default, it will show the bots permissions, for the current channel.
        """
        perms = []
        target = target or _target or ctx.me
        channel = channel or ctx.channel
        channel_perms = [x for x, y in channel.permissions_for(target) if y is True]
        for perm, value in target.guild_permissions:
            perms.append([perm.replace('guild', 'server').replace('_', ' ').title(), str(value),
                          str(perm in channel_perms)])
        table = tabulate.tabulate(perms, tablefmt="orgtbl", headers=['Permissions', 'Server', 'Channel'])
        embed = discord.Embed(description=f"```py\n{table}\n```")
        embed.set_footer(text='"Channel" permissions consider Server, Channel and Member overwrites.')
        embed.set_author(name=f'{target}\'s permissions for {channel}'[0:256], icon_url=target.display_avatar.url)
        await ctx.send(embed=embed)
