import aiohttp
import datetime
import discord
import re
import typing
import yaml
from collections import Counter

from discord.ext import commands, tasks, menus

from ozbot import helpers, constants
from ozbot.__main__ import Ozbot


class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, _):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, _):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


async def namecheck(argument):
    async with aiohttp.ClientSession() as cs:
        async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as r:
            if r.status == 204:
                user = None
            elif r.status == 400:
                user = None
            else:
                res = await r.json()
                user = res["name"]
            return user


class Moderation(commands.Cog):
    """⚖ Moderation commands."""

    def __init__(self, bot):
        self.bot: Ozbot = bot
        self.autounmute.start()

        # ------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            guild = full_yaml['guildID']
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(guild).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml
        self.server = self.bot.get_guild(guild)
        self.console = self.bot.get_channel(full_yaml['ConsoleCommandsChannel'])

    def cog_unload(self):
        self.autounmute.cancel()

    async def cog_check(self, ctx: commands.Context) -> bool:
        mod_role = await self.bot.db.execute('SELECT object_id FROM config WHERE type = $1', 'moderation_role')
        if ctx.author.guild_permissions.administrator or ctx.author._roles.has(mod_role):
            return True
        raise commands.NotOwner()

    @tasks.loop()
    async def autounmute(self):
        # if you don't care about keeping records of old tasks, remove this WHERE and change the UPDATE to DELETE
        next_task = await self.bot.db.fetchrow('SELECT * FROM selfmutes ORDER BY end_time LIMIT 1')
        # if no remaining tasks, stop the loop
        if next_task is None:
            self.autounmute.cancel()
            return
        # sleep until the task should be done
        await discord.utils.sleep_until(next_task['end_time'])

        urole = self.server.get_role(self.yaml_data['MuteRole'])
        umember = self.server.get_member(next_task['member_id'])
        await umember.remove_roles(urole, reason=f"end of self-mute for {umember} ({umember.id})")

        await self.bot.db.execute('DELETE FROM selfmutes WHERE member_id = $1', next_task['member_id'])

    @autounmute.before_loop
    async def wait_for_bot_ready(self):
        await self.bot.wait_until_ready()

    if True:
        # Source Code Form:
        # command: https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L1181-L1408
        # Origina Command Licensed under MPL 2.0: https://github.com/Rapptz/RoboDanny/blob/rewrite/LICENSE.txt

        @commands.group(aliases=['purge', 'clear', 'clean'])
        @commands.guild_only()
        @commands.has_permissions(manage_messages=True)
        @commands.bot_has_permissions(manage_messages=True)
        async def remove(self, ctx, search: typing.Optional[int]):
            """
            Removes messages that meet a criteria. In order to use this command, you must have Manage Messages permissions.

            Remember that the bot needs Manage Messages as well. These commands cannot be used in a private message.

            When the command is done doing its work, you will get a message detailing which users got removed and how many messages got removed.

            Note: If ran without any sub-commands, it will remove all messages that are NOT pinned to the channel. use "remove all <amount>" to remove everything
            """

            if ctx.invoked_subcommand is None:
                await self.do_removal(ctx, search, lambda e: not e.pinned)

        @staticmethod
        async def do_removal(ctx, limit, predicate, *, before=None, after=None):
            if limit > 2000:
                return await ctx.send(f'Too many messages to search given ({limit}/2000)')

            if before is None:
                before = ctx.message
            else:
                before = discord.Object(id=before)

            if after is not None:
                after = discord.Object(id=after)

            try:
                deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
            except discord.Forbidden:
                return await ctx.send('I do not have permissions to delete messages.')
            except discord.HTTPException as e:
                return await ctx.send(f'Error: {e} (try a smaller search?)')

            spammers = Counter(m.author.display_name for m in deleted)
            deleted = len(deleted)
            messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
            if deleted:
                messages.append('')
                spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
                messages.extend(f'**{name}**: {count}' for name, count in spammers)

            to_send = '\n'.join(messages)

            if len(to_send) > 2000:
                await ctx.send(f'Successfully removed {deleted} messages.')
            else:
                await ctx.send(to_send)

        @remove.command(aliases=['embed'])
        async def embeds(self, ctx, search=100):
            """Removes messages that have embeds in them."""
            await self.do_removal(ctx, search, lambda e: len(e.embeds))

        @remove.command()
        async def files(self, ctx, search=100):
            """Removes messages that have attachments in them."""
            await self.do_removal(ctx, search, lambda e: len(e.attachments))

        @remove.command()
        async def images(self, ctx, search=100):
            """Removes messages that have embeds or attachments."""
            await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

        @remove.command(name='all')
        async def remove_remove_all(self, ctx, search=100):
            """Removes all messages."""
            await self.do_removal(ctx, search, lambda e: True)

        @remove.command()
        async def user(self, ctx, member: discord.Member, search=100):
            """Removes all messages by the member."""
            await self.do_removal(ctx, search, lambda e: e.author == member)

        @remove.command()
        async def contains(self, ctx, *, substr: str):
            """Removes all messages containing a substring.
            The substring must be at least 3 characters long.
            """
            if len(substr) < 3:
                await ctx.send('The substring length must be at least 3 characters.')
            else:
                await self.do_removal(ctx, 100, lambda e: substr in e.content)

        @remove.command(name='bot', aliases=['bots'])
        async def remove_bot(self, ctx, prefix=None, search=100):
            """Removes a bot user's messages and messages with their optional prefix."""

            def predicate(m):
                return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

            await self.do_removal(ctx, search, predicate)

        @remove.command(name='deaths', aliases=['death'])
        async def remove_dsrv_deaths(self, ctx, search=100):
            """Removes all messages that may be deaths from DiscordSRV (has a black embed color)."""

            def predicate(m):
                if m.embeds:
                    return m.embeds[0].color == discord.Color(0x000000)

            await self.do_removal(ctx, search, predicate)

        @remove.command(name='emoji', aliases=['emojis'])
        async def remove_emoji(self, ctx, search=100):
            """Removes all messages containing custom emoji."""
            custom_emoji = re.compile(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>')

            def predicate(m):
                return custom_emoji.search(m.content)

            await self.do_removal(ctx, search, predicate)

        @remove.command(name='reactions')
        async def remove_reactions(self, ctx, search=100):
            """Removes all reactions from messages that have them."""

            if search > 2000:
                return await ctx.send(f'Too many messages to search for ({search}/2000)')

            total_reactions = 0
            async for message in ctx.history(limit=search, before=ctx.message):
                if len(message.reactions):
                    total_reactions += sum(r.count for r in message.reactions)
                    await message.clear_reactions()

            await ctx.send(f'Successfully removed {total_reactions} reactions.')

    @commands.command()
    async def gameban(self, ctx, *, user: typing.Union[discord.User, str]):
        """ Bans a user from the in-game """
        if isinstance(user, discord.User):
            await self.bot.db.fetchval()


def setup(bot):
    bot.add_cog(Moderation(bot))
