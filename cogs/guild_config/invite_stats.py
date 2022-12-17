import collections
import collections
import operator
from typing import Optional

import discord
import tabulate
from discord.ext import commands

from bot import CustomContext
from ._base import ConfigBase


class InviteStats(ConfigBase):
    @commands.guild_only()
    @commands.command(usage=None)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def invitestats(
        self, ctx: CustomContext, *, _=None, return_embed: bool = False, guild_id: int = None
    ) -> Optional[discord.Embed]:
        """Displays the top 10 most used invites in the guild, and the top 10 inviters."""
        max_table_length = 10
        # PEP8 + same code, more readability
        invites = self.bot.invites.get(guild_id or ctx.guild.id, None)

        # falsey check for None or {}
        if not invites:
            # if there is no invites send this information
            # in an embed and return
            if return_embed:
                embed = discord.Embed(
                    title="Something Went Wrong...",
                    description="No invites found." "\nDo I have `Manage Server` permissions?",
                    colour=discord.Colour.red(),
                )
                return embed
            raise commands.BadArgument('I couldn\'t find any Invites. (try again?)')

        # if you got here there are invites in the cache
        if return_embed is not True:
            embed = discord.Embed(colour=discord.Colour.green(), title=f'{ctx.guild.name}\'s invite stats')
        else:
            embed = discord.Embed(colour=ctx.colour, title=f'{ctx.guild.name}', timestamp=ctx.message.created_at)
        # sort the invites by the amount of uses
        # by default this would make it in increasing
        # order so we pass True to the reverse kwarg
        invites = sorted(invites.values(), key=lambda i: i.uses, reverse=True)
        # if there are 10 or more invites in the cache we will
        # display 10 invites, otherwise display the amount
        # of invites
        amount = max_table_length if len(invites) >= max_table_length else len(invites)
        # list comp on the sorted invites and then
        # join it into one string with str.join
        description = (
            f'**__Top server {amount} invites__**\n```py\n'
            + tabulate.tabulate(
                [
                    (
                        f'{i + 1}. [{invites[i].code if return_embed is False else "*"*(len(invites[i].code)-4)}] {invites[i].inviter.name}',
                        f'{invites[i].uses}',
                    )
                    for i in range(amount)
                ],
                headers=['Invite', 'Uses'],
            )
            + (
                f'\n``` ___There are {len(invites) - max_table_length} more invites in this server.___\n'
                if len(invites) > max_table_length
                else '\n```'
            )
        )

        inv = collections.defaultdict(int)
        for t in [(invite.inviter.name, invite.uses) for invite in invites]:
            inv[t[0]] += t[1]
        invites = dict(inv)
        invites = sorted(invites.items(), key=operator.itemgetter(1), reverse=True)
        value = max_table_length if len(invites) >= max_table_length else len(invites)
        table = tabulate.tabulate(invites[0:value], headers=['Inviter', 'Added'])

        description = (
            description
            + f'\n**__Top server {value} inviters__**\n```\n'
            + table
            + '```'
            + (
                f' ___There are {len(invites) - max_table_length} more inviters in this server.___'
                if len(invites) > max_table_length
                else ''
            )
        )

        if return_embed is True:
            description += '\nInvite codes hidden for privacy reasons. See\nthe `invite-stats` command for invite codes.'

        embed.description = description

        if return_embed is True:
            embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
            return embed
        await ctx.send(embed=embed)
