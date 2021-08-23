import argparse
import discord
import re
import shlex
import typing
from collections import Counter

from discord.ext import commands, menus

import errors


class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


def can_execute_action(ctx, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{ctx.author} (ID: {ctx.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret


def safe_reason_append(base, to_append):
    appended = base + f'({to_append})'
    if len(appended) > 512:
        return base
    return appended


class BanEmbed(menus.ListPageSource):
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text=f"To unban do db.unban [entry]\nMore user info do db.baninfo [entry]")
        return embed


class Moderation(commands.Cog):
    """🔨Moderation commands! 👮‍♂️"""

    def __init__(self, bot):
        self.bot = bot

    # --------------- FUNCTIONS ---------------#

    @staticmethod
    async def perms_error(ctx):
        await ctx.message.add_reaction('🚫')
        await ctx.message.delete(delay=5)
        return

    @staticmethod
    async def error_message(ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        await ctx.message.delete(delay=5)

    # --------------------------------------------------------------#
    # ------------------------ PREFIX ------------------------------#
    # --------------------------------------------------------------#

    @commands.command()
    @commands.guild_only()
    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    async def prefix(self, ctx, new: typing.Optional[str] = None):
        """🎇NEW changes the bot's prefix for this server.\nuse quotes to add spaces: %PRE%prefix \"duck \" """

        old = await self.bot.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not new:
            old = old or 'db.'
            await ctx.send(f"my prefix here is `{old}`")
            return

        if len(new) > 10:
            return await ctx.send("Prefixes can only be up to 10 characters")
        if not old:
            await self.bot.db.execute('INSERT INTO prefixes(guild_id, prefix) VALUES ($1, $2)', ctx.guild.id, new)
            await ctx.send(f"**Prefix changed:**\n`{old}` ➡ `{new}`")
        elif old != new:
            await self.bot.db.execute('UPDATE prefixes SET prefix = $1 WHERE guild_id = $2', new, ctx.guild.id)
            await ctx.send(f"**Prefix changed:**\n`{old}` ➡ `{new}`")
        else:
            await ctx.send(f"`{new}` is already my prefix")

    # ------------------------------------------------------------#
    # ------------------------ KICK ------------------------------#
    # ------------------------------------------------------------#

    @commands.command(help="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: typing.Optional[str] = None):
        if member == ctx.author:
            await self.error_message(ctx, 'You can\'t kick yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            return await self.error_message(ctx, 'I\'m not high enough in role hierarchy to kick that member!')
        if member.top_role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id:
            mem_embed = discord.Embed(description=f"**{ctx.message.author}** has kicked you from **{ctx.guild.name}**",
                                      color=ctx.me.color)
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            try:
                await member.send(embed=mem_embed)
                dm_success = '✅'
            except discord.HTTPException:
                dm_success = '❌'
            await member.kick(reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
            if reason:
                actionReason = f"\n```\nreason: {reason}```"
            else:
                actionReason = ''

            embed = discord.Embed(
                description=f"{ctx.author.mention} kicked **{member}**({member.mention}){actionReason}",
                color=ctx.me.color)
            embed.set_footer(text=f'ID: {member.id} | DM sent: {dm_success}')
            await ctx.send(embed=embed)

        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

    # -----------------------------------------------------------#
    # ------------------------ BAN ------------------------------#
    # -----------------------------------------------------------#

    @commands.command(help="Bans a member from the server")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    async def ban(self, ctx, user: typing.Union[discord.Member, discord.User], *, reason: typing.Optional[str] = None):
        member = user
        if member == ctx.author: return await self.error_message(ctx, 'You can\'t ban yourself')
        if isinstance(user, discord.Member):
            if member.top_role >= ctx.me.top_role: return await self.error_message(ctx,
                                                                                   'I\'m not high enough in role hierarchy to ban that member!')
            if member.top_role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id:
                mem_embed = discord.Embed(
                    description=f"**{ctx.message.author}** has banned you from **{ctx.guild.name}**",
                    color=ctx.me.color)
                if isinstance(reason, str): mem_embed.set_footer(text=f'reason: {reason}')
                try:
                    await member.send(embed=mem_embed)
                    dm_success = '✅'
                except discord.HTTPException:
                    dm_success = '❌'
            else:
                await self.error_message(ctx, 'Member is higher than you in role hierarchy')
                return

        else:
            dm_success = '❌'

        if isinstance(reason, str):
            actionReason = f"\n```\nreason: {reason}```"
        else:
            actionReason = ''

        embed = discord.Embed(description=f"{ctx.author.mention} banned **{member}**({member.mention}){actionReason}",
                              color=ctx.me.color)
        embed.set_footer(text=f'ID: {member.id} | DM sent: {dm_success}')
        await ctx.send(embed=embed)

        await ctx.guild.ban(member, reason=f"{ctx.author} (ID: {ctx.author.id}): {reason or ''}")

    # ------------------------------------------------------------#
    # ------------------------ NICK ------------------------------#
    # ------------------------------------------------------------#

    @commands.command(help="Sets yours or someone else's nick # leave empty to remove nick", aliases=['sn', 'nick'],
                      usage="<member> [new nick]")
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_nicknames=True)
    async def setnick(self, ctx, member: discord.Member, *, new: str = 'None'):
        if len(new) > 32:
            raise commands.BadArgument(f'Nickname too long. {len(new)}/32')
        if not can_execute_action(ctx, ctx.author, member):
            raise commands.MissingPermissions('role hierarchy error')
        new = new or member.name
        old = member.display_name
        try:
            await member.edit(nick=new)
            await ctx.send(f"✏ {ctx.author.mention} nick for {member}"
                           f"\n**`{old}`** -> **`{new}`**")
        except discord.Forbidden:
            raise commands.BadArgument(f'Nickname too long. {len(new)}/32')
        except discord.HTTPException:
            await ctx.message.add_reaction('#️⃣')
            await ctx.message.add_reaction('3️⃣')
            await ctx.message.add_reaction('2️⃣')
            return

    # -------------------------------------------------------------#
    # ------------------------ PURGE ------------------------------#
    # -------------------------------------------------------------#

    @commands.group(aliases=['purge', 'clear', 'delete', 'clean'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def remove(self, ctx, search: typing.Optional[int] = 100):
        """```yaml
        Removes messages that meet a criteria. In order to use this command, you must have Manage Messages permissions.

        Remember that the bot needs Manage Messages as well. These commands cannot be used in a private message.

        When the command is done doing its work, you will get a message detailing which users got removed and how many messages got removed.

        Note: If ran without any sub-commands, it will remove all messages that are NOT pinned to the channel. use "remove all <amount>" to remove everything
        ```
        """

        if ctx.invoked_subcommand is None:
            await self.do_removal(ctx, search, lambda e: not e.pinned)

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None):
        if limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
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
            await ctx.send(f'Successfully removed {deleted} messages.', delete_after=10)
        else:
            await ctx.send(to_send, delete_after=10)

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
    async def remove_bot(self, ctx, prefix: typing.Optional[str] = None, search=100):
        """Removes a bot user's messages and messages with their optional prefix."""

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await self.do_removal(ctx, search, predicate)

    @remove.command(name='emoji', aliases=['emojis'])
    async def remove_emoji(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>')

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

    @remove.group()
    async def custom(self, ctx, *, args: str):
        """A more advanced purge command.
        do "%PRE%help remove custom" for usage.
        """
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument('--user', nargs='+')
        parser.add_argument('--contains', nargs='+')
        parser.add_argument('--starts', nargs='+')
        parser.add_argument('--ends', nargs='+')
        parser.add_argument('--or', action='store_true', dest='_or')
        parser.add_argument('--not', action='store_true', dest='_not')
        parser.add_argument('--emoji', action='store_true')
        parser.add_argument('--bot', action='store_const', const=lambda m: m.author.bot)
        parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
        parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
        parser.add_argument('--reactions', action='store_const', const=lambda m: len(m.reactions))
        parser.add_argument('--search', type=int)
        parser.add_argument('--after', type=int)
        parser.add_argument('--before', type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            await ctx.send(str(e))
            return

        predicates = []
        if args.bot:
            predicates.append(args.bot)

        if args.embeds:
            predicates.append(args.embeds)

        if args.files:
            predicates.append(args.files)

        if args.reactions:
            predicates.append(args.reactions)

        if args.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if args.user:
            users = []
            converter = commands.MemberConverter()
            for u in args.user:
                try:
                    user = await converter.convert(ctx, u)
                    users.append(user)
                except Exception as e:
                    await ctx.send(str(e))
                    return

            predicates.append(lambda m: m.author in users)

        if args.contains:
            predicates.append(lambda m: any(sub in m.content for sub in args.contains))

        if args.starts:
            predicates.append(lambda m: any(m.content.startswith(s) for s in args.starts))

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = all if not args._or else any

        def predicate(m):
            r = op(p(m) for p in predicates)
            if args._not:
                return not r
            return r

        if args.after:
            if args.search is None:
                args.search = 2000

        if args.search is None:
            args.search = 100

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000
        await self.do_removal(ctx, args.search, predicate, before=args.before, after=args.after)

    @custom.command(name="readme")
    async def remove_custom_readme(self, ctx):
        """A more advanced purge command.
        This command uses a powerful "command line" syntax.
        Most options support multiple values to indicate 'any' match.
        If the value has spaces it must be quoted.
        The messages are only deleted if all options are met unless
        the --or flag is passed, in which case only if any is met.

        The following options are valid.
         --user: A mention or name of the user to remove.
         --contains: A substring to search for in the message.
         --starts: A substring to search if the message starts with.
         --ends: A substring to search if the message ends with.
         --search: Messages to search. Default 100. Max 2000.
         --after: Messages after this message ID.
         --before: Messages before this message ID.

        Flag options (no arguments):
         --bot: Check if it's a bot user.
         --embeds: Checks for embeds.
         --files: Checks for attachments.
         --emoji: Checks for custom emoji.
         --reactions: Checks for rections.
         --or: Use logical OR for ALL options.
         --not: Use logical NOT for ALL options.
        """
        await ctx.send("hi")

    @commands.command()
    async def cleanup(self, ctx, amount: int = 25):
        """
        Cleans up the bot's messages. it defaults to 25 messages. if you or the bot don't have manage_messages permission, the search will be limited to 25 messages.
        """
        if amount > 25:
            if not ctx.channel.permissions_for(ctx.author).manage_messages:
                await ctx.send("You must have `manage_messages` permission to perform a search greater than 25")
                return
            if not ctx.channel.permissions_for(ctx.me).manage_messages:
                await ctx.send("I need the `manage_messages` permission to perform a search greater than 25")
                return

        def check(msg):
            return msg.author == ctx.me

        if ctx.channel.permissions_for(ctx.me).manage_messages:
            deleted = await ctx.channel.purge(limit=amount, check=check)
        else:
            deleted = await ctx.channel.purge(limit=amount, check=check, bulk=False)
        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)
        if len(to_send) > 2000:
            await ctx.send(f'Successfully removed {deleted} messages.', delete_after=10)
        else:
            await ctx.send(to_send, delete_after=10)

    # ------------------------------------------------------------------------------#
    # --------------------------------- UNBAN --------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="unbans a member # run without arguments to get a list of entries")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def unban(self, ctx, entry: int):
        number = entry
        if number <= 0:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return

        try:
            ban_entry = bans[number]
        except:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"That member was not found. \nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        await ctx.guild.unban(ban_entry.user)
        await ctx.send(f'unbanned **{ban_entry.user}**')

    # ------------------------------------------------------------------------------#
    # -------------------------------- BAN LIST ------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="Gets a list of bans in the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def bans(self, ctx):
        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return
        desc = []
        number = 1
        for ban_entry in bans:
            desc.append(f"**{number}) {ban_entry.user}**")
            number = number + 1
        pages = menus.MenuPages(source=BanEmbed(desc), clear_reactions_after=True)
        await pages.start(ctx)

    # ------------------------------------------------------------------------------#
    # -------------------------------- BAN INFO ------------------------------------#
    # ------------------------------------------------------------------------------#

    @commands.command(help="brings info about a ban # run without arguments to get a list of entries", usage="[entry]")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, ban_members=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def baninfo(self, ctx, number: typing.Optional[int]):
        if not ctx.channel.permissions_for(ctx.me).ban_members:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not number:
            try:
                bans = await ctx.guild.bans()
            except:
                await ctx.send("i'm missing the ban_members permission :pensive:")
                return
            if not bans:
                await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
                return

            desc = []
            number = 1
            for ban_entry in bans:
                desc.append(f"**{number}) {ban_entry.user}**")
                number = number + 1
            pages = menus.MenuPages(source=BanEmbed(desc), clear_reactions_after=True)
            await pages.start(ctx)
            return

        if number <= 0:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"__number__ must be greater than 1\nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        number = number - 1

        try:
            bans = await ctx.guild.bans()
        except:
            await ctx.send("i'm missing the ban_members permission :pensive:")
            return
        if not bans:
            await ctx.send(embed=discord.Embed(title="There are no banned users in this server"))
            return
        try:
            ban_entry = bans[number]
        except:
            embed = discord.Embed(color=0xFF0000,
                                  description=f"That member was not found. \nsyntax: `{ctx.prefix}{ctx.command} {ctx.command.usage}`\n To get the number use the `{ctx.prefix}{ctx.command}` command")
            await ctx.send(embed=embed)
            return

        date = ban_entry.user.created_at
        embed = discord.Embed(color=ctx.me.color,
                              description=f"""```yaml
       user: {ban_entry.user}
    user id: {ban_entry.user.id}
     reason: {ban_entry.reason}
 created at: {date.strftime("%b %-d %Y at %-H:%M")} UTC
```""")
        embed.set_author(name=ban_entry.user, icon_url=ban_entry.user.avatar.url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Moderation(bot))
