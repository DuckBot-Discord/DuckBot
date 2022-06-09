import pprint
import textwrap
from typing import Any, List

import discord
from discord.ext import commands

from DuckBot.__main__ import DuckBot
from ..helpers.context import CustomContext


async def ensure_table(bot: DuckBot):
    # Create the table if it doesn't exist
    try:
        await bot.db.execute("CREATE TYPE t_type AS ENUM ('user', 'role')")
    except:  # noqa
        pass
    query = """        
        CREATE TABLE IF NOT EXISTS overwrites (
            guild_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            target_id BIGINT NOT NULL,
            target_type t_type NOT NULL,
            allow BIGINT NOT NULL,
            deny BIGINT NOT NULL,
            PRIMARY KEY (guild_id, channel_id, target_id, target_type)
        );
    """
    await bot.db.execute(query)


async def setup(bot: DuckBot):
    await bot.add_cog(Test(bot))
    bot.loop.create_task(ensure_table(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = "🧪"
        self.select_brief = "Beta Commands (WIP)"

    async def cog_check(self, ctx: CustomContext) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True
        raise commands.NotOwner("You are not the bot owner.")

    @commands.command(name="osave")
    async def _osave(self, ctx: CustomContext, *, channel: discord.abc.GuildChannel):
        """
        saves the overwrites of the channel to the database
        """
        channel = channel or ctx.channel

        to_execute = []
        for target, overwrite in channel.overwrites.items():
            base: List[Any] = [channel.guild.id, channel.id, target.id]

            if isinstance(target, discord.Role):
                base.append("role")
            else:
                base.append("user")

            allow, deny = overwrite.pair()
            base.append(allow.value)
            base.append(deny.value)

            to_execute.append(base)

        query = """
            INSERT INTO overwrites VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (guild_id, channel_id, target_id, target_type)
                DO UPDATE SET allow = $5, deny = $6
        """
        await ctx.bot.db.execute(
            "DELETE FROM overwrites WHERE guild_id = $1 AND channel_id = $2",
            channel.guild.id,
            channel.id,
        )
        await ctx.bot.db.executemany(query, to_execute)
        await ctx.send("Saved.")

    @commands.command(name="osee")
    async def _osee(self, ctx: CustomContext, *, channel: discord.abc.GuildChannel):
        """
        gets an overwrite from the database
        """
        channel = channel or ctx.channel
        entries = await ctx.bot.db.fetch(
            """
            SELECT target_id, target_type, allow, deny
            FROM overwrites
            WHERE guild_id = $1 AND channel_id = $2
        """,
            channel.guild.id,
            channel.id,
        )

        if not entries:
            raise commands.BadArgument(f"Overwrites for #{channel} are not in the database!")

        fmt = []
        for entry in entries:
            target_id, target_type, allow, deny = entry
            method = ctx.guild.get_role if target_type == "role" else ctx.guild.get_member
            target = method(target_id)
            if not target:
                # The target is no longer present
                # in the guild, or we can't access
                # it, so we ignore it.
                continue

            allow = discord.Permissions(allow)
            deny = discord.Permissions(deny)
            overwrite = discord.PermissionOverwrite.from_pair(allow, deny)

            if isinstance(target, discord.Member):
                etype = 'member: '
            else:
                etype = 'role: '
            header = f"{etype}{target}"
            fmt.append(header)
            perms = []
            for name, value in overwrite:
                if value is None:
                    continue
                perms.append(ctx.square_tick(value, name))
            if perms:
                fmt.append(textwrap.indent('\n'.join(perms), ' ' * len(header)))
            else:
                fmt[-1] += ' (No Permissions)'

        NL = '\n'
        if isinstance(ctx.author, discord.Member):
            mobile = ctx.author.is_on_mobile()
        else:
            mobile = False

        await ctx.send(
            f"```\nOverwrites for channel #{channel}:\n{textwrap.indent(NL.join(fmt), '  ')}\n```",
            maybe_attachment=not mobile,
            gist=mobile,
            extension='txt',
        )
