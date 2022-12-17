import difflib
import random

import discord
from discord.ext import commands

import errors
from bot import DuckBot
from helpers.context import CustomContext


class BannedMember(commands.Converter):
    async def convert(self, ctx: CustomContext, argument):  # noqa
        await ctx.typing()
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = [ban async for ban in ctx.guild.bans()]
        if not (entity := discord.utils.find(lambda u: str(u.user).lower() == argument.lower(), ban_list)):
            entity = discord.utils.find(lambda u: str(u.user.name).lower() == argument.lower(), ban_list)
            if not entity:
                matches = difflib.get_close_matches(argument, [str(u.user.name) for u in ban_list])
                if matches:
                    entity = discord.utils.find(lambda u: str(u.user.name) == matches[0], ban_list)
                    if entity:
                        val = await ctx.confirm(
                            f'Found closest match: **{entity.user}**. Do you want me to unban them?',
                            delete_after_cancel=True,
                            delete_after_confirm=True,
                            delete_after_timeout=False,
                            timeout=60,
                            buttons=((None, 'Yes', discord.ButtonStyle.green), (None, 'No', discord.ButtonStyle.grey)),
                        )  # noqa
                        if val is None:
                            raise errors.NoHideout
                        elif val is False:
                            try:
                                await ctx.message.add_reaction(random.choice(ctx.bot.constants.DONE))
                            except discord.HTTPException:
                                pass
                            raise errors.NoHideout

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity


class ModerationBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.bot = bot

    @staticmethod
    def can_execute_action(ctx, user, target):
        if isinstance(target, discord.Member):
            return user == ctx.guild.owner or (user.top_role > target.top_role and target != ctx.guild.owner)
        elif isinstance(target, discord.User):
            return True
        raise TypeError(f'argument \'target\' expected discord.User, received {type(target)} instead')

    @staticmethod
    def bot_can_execute_action(ctx: commands.Context, target: discord.Member):
        if isinstance(target, discord.Member):
            if target.top_role > ctx.guild.me.top_role:
                raise commands.BadArgument('This member has a higher role than me.')
            elif target == ctx.guild.owner:
                raise commands.BadArgument('I cannot perform that action, as the target is the owner.')
            elif target == ctx.guild.me:
                raise commands.BadArgument('I cannot perform that action on myself.')
            return True
