import argparse
import asyncio
import discord
import re
import shlex
import typing
import yaml
from collections import Counter

import helpers
from discord.ext import commands, menus

from ospbot.files import constants, helper


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class banembed(menus.ListPageSource):
    def __init__(self, data, per_page=15):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"Server bans ({len(entries)})",
                              description="\n".join(entries))
        embed.set_footer(text=f"To unban do db.unban [entry]\nMore user info do db.baninfo [entry]")
        return embed


class Confirm(menus.Menu):
    def remove__init__(self, msg):
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


class moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # ------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(full_yaml['guildID']).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml

    # --------------- FUNCTIONS ---------------#

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(self.yaml_data['ReactionTimeout'])
        try:
            await ctx.message.delete()
            return
        except:
            return

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
        await asyncio.sleep(self.yaml_data['ErrorMessageTimeout'])
        try:
            await ctx.message.delete()
            return
        except:
            return

    def get_user_badges(self, user, bot: bool = False):
        flags = dict(user.public_flags)

        if bot is True:
            return True if flags['verified_bot'] else False

        if user.premium_since:
            flags['premium_since'] = True
        else:
            flags['premium_since'] = False

        user_flags = []
        for flag, emoji in constants.USER_FLAGS.items():
            if flags[flag]:
                user_flags.append(emoji)

        return ' '.join(user_flags) if user_flags else None

    @commands.command(help="Shows a user's avatar", alias=['avatar'])
    async def pfp(self, ctx, user: typing.Optional[discord.Member]):
        user = user or ctx.author
        embed = discord.Embed(color=ctx.me.color)
        embed.description = f"[PNG]({user.avatar.replace(format='png', size=2048).url}) **|** [JPG]({user.avatar.replace(format='jpg', size=2048).url}) **|** [WEBP]({user.avatar.replace(format='webp', size=2048).url})"
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['uinfo', 'ui', 'whois', 'whoami'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, *, member: typing.Optional[discord.Member]):
        """
        Shows a user's information. If not specified, shows your own.
        """

        member = member or ctx.author

        # BIRTHDAY
        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', member.id)
        if current_birthday:
            now = discord.utils.utcnow().date()
            delta = now - current_birthday
            age = int(delta.days / 365.2425)
            birthday = f"`{current_birthday.strftime('%B %d, %Y')} ({age} Y/O)`"
        else:
            birthday = "undefined"

        embed = discord.Embed(color=(member.color if member.color != discord.Colour.default() else discord.Embed.Empty))
        embed.set_author(name=member, icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name=f"{constants.INFORMATION_SOURCE} General information",
                        value=f"**ID:** {member.id}"
                              f"\n**Name:** {member.name}"
                              f"\n╰ **Nick:** {(member.nick or '✖')}"
                              f"\n**Owner:** {constants.CUSTOM_TICKS[True] if member == member.guild.owner else constants.CUSTOM_TICKS[False]} • "
                              f"**Bot:** {constants.CUSTOM_TICKS[True] if member.bot else constants.CUSTOM_TICKS[False]}"
                              f"\n**Birthday**: {birthday}", inline=True)

        embed.add_field(name=f"{constants.STORE_TAG} Badges",
                        value=(self.get_user_badges(member) or "No Badges") + '\u200b', inline=True)

        embed.add_field(name=f"{constants.INVITE} Created At",
                        value=f"╰ {discord.utils.format_dt(member.created_at, style='f')} "
                              f"({discord.utils.format_dt(member.created_at, style='R')})",
                        inline=False)

        embed.add_field(name=f"{constants.JOINED_SERVER} Created At",
                        value=(f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                               f"({discord.utils.format_dt(member.joined_at, style='R')})"
                               f"\n\u200b \u200b \u200b \u200b ╰ {constants.LEFT_SERVER} **Join Position:** "
                               f"{sorted(ctx.guild.members, key=lambda m: m.joined_at).index(member) + 1}")
                        if member else "Could not get data",
                        inline=False)

        perms = helper.get_perms(member.guild_permissions)
        if perms:
            embed.add_field(name=f"{constants.STORE_TAG} Staff Perms:",
                            value=f"`{'` `'.join(perms)}`", inline=False)

        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        if roles:
            embed.add_field(name=f"{constants.ROLES_ICON} Roles:",
                            value=" ".join(roles), inline=False)

        if member.premium_since:
            embed.add_field(name=f"{constants.BOOST} Boosting since:",
                            value=f"╰ {discord.utils.format_dt(member.premium_since, style='f')} "
                                  f"({discord.utils.format_dt(member.premium_since, style='R')})",
                            inline=False)

        return await ctx.send(embed=embed)


    # ------------------------------------------------------------#
    # ------------------------ KICK ------------------------------#
    # ------------------------------------------------------------#

    @commands.command(help="kicks specified member")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to kick')
            return
        elif member == ctx.author:
            await self.error_message(ctx, 'You can\'t kick yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            await self.error_message(ctx, 'I\'m not high enough in role hierarchy to kick that member!')
            return
        if member.top_role <= ctx.author.top_role:
            if member.guild_permissions.ban_members == False or member.guild_permissions.kick_members == False:
                try:
                    mem_embed = discord.Embed(
                        description=f"**{ctx.message.author}** has kicked you from **{ctx.guild.name}**",
                        color=ctx.me.color)
                    if reason: mem_embed.set_footer(text=f'reason: {reason}')
                    await member.send(embed=mem_embed)
                    await member.kick(reason=reason)
                    if reason:
                        embed = discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed = discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}""",
                                              color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ✅')
                    await ctx.send(embed=embed)
                except discord.HTTPException:
                    await member.kick(reason=reason)
                    if reason:
                        embed = discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed = discord.Embed(description=f"""{ctx.author.mention} kicked {member.mention}""",
                                              color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ❌')
                    await ctx.send(embed=embed)
            else:
                await self.error_message(ctx, 'you can\'t kick another moderator')
                return
        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

    # -----------------------------------------------------------#
    # ------------------------ BAN ------------------------------#
    # -----------------------------------------------------------#

    @commands.command(help="Bans specified member")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to ban')
            return
        elif member == ctx.author:
            await self.error_message(ctx, 'You can\'t ban yourself')
            return
        elif member.top_role >= ctx.me.top_role:
            await self.error_message(ctx, 'I\'m not high enough in role hierarchy to ban that member!')
            return
        if member.top_role <= ctx.author.top_role:
            if member.guild_permissions.ban_members == False or member.guild_permissions.kick_members == False:
                try:
                    mem_embed = discord.Embed(description=f"A moderator has banned you from **{ctx.guild.name}**",
                                              color=ctx.me.color)
                    if reason: mem_embed.set_footer(text=f'reason: {reason}')
                    await member.send(embed=mem_embed)
                    await member.ban(reason=reason)
                    if reason:
                        embed = discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed = discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}""",
                                              color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ✅')
                    await ctx.send(embed=embed)
                except discord.HTTPException:
                    await member.ban(reason=reason)
                    if reason:
                        embed = discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}
```reason: {reason}```""", color=ctx.me.color)
                    else:
                        embed = discord.Embed(description=f"""{ctx.author.mention} banned {member.mention}""",
                                              color=ctx.me.color)
                    embed.set_footer(text=f'{member.id} | DM sent: ❌')
                    await ctx.send(embed=embed)
            else:
                await self.error_message(ctx, 'you can\'t ban another moderator!')
                return

        else:
            await self.error_message(ctx, 'Member is higher than you in role hierarchy')
            return

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await self.perms_error(ctx)

    # ------------------------------------------------------------#
    # ------------------------ NICK ------------------------------#
    # ------------------------------------------------------------#

    @commands.command(aliases=['sn', 'nick'], help="Edits user's server nickname")
    @commands.has_permissions(manage_messages=True, change_nickname=True)
    async def setnick(self, ctx, member: typing.Optional[discord.Member], *, new: typing.Optional[str] = 'None'):
        if member == None:
            if ctx.channel.permissions_for(ctx.author).manage_nicknames:
                await ctx.send("`.nick [member] (newNick)` - You must specify a member", delete_after=10)
                await asyncio.sleep(10)
                await ctx.message.delete()
            return
        if new == 'None':
            new = f'{member.name}'
        else:
            new = new
        old = f'{member.nick}'
        if old == 'None':
            old = f'{member.name}'
        else:
            old = old
        if member == ctx.author and ctx.channel.permissions_for(ctx.author).change_nickname:
            try:
                await member.edit(nick=new)
                await ctx.send(f"""✏ {ctx.author.mention} nick for {member}
**`{old}`** -> **`{new}`**""")
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return
            except discord.Forbidden:
                await self.error_message(ctx, 'Bot not high enough in role hierarchy')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
                return
        elif ctx.channel.permissions_for(ctx.author).manage_nicknames:
            if member.top_role >= ctx.author.top_role:
                await self.error_message(ctx, "⚠ Cannot edit nick for members equal or above yourself!")
                return
            try:
                await member.edit(nick=new)
                await ctx.send(f"""✏ {ctx.author.mention} edited nick for **{member}**
**`{old}`** -> **`{new}`**""")
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return
            except discord.Forbidden:
                await self.error_message(ctx, 'Bot not high enough in role hierarchy')
                return
            except discord.HTTPException:
                await ctx.message.add_reaction('#️⃣')
                await ctx.message.add_reaction('3️⃣')
                await ctx.message.add_reaction('2️⃣')
        elif member == ctx.author and ctx.channel.permissions_for(ctx.author).change_nickname:
            await self.error_message(ctx, f"""You can only change your own nick!
> !nick {ctx.author.mention} `<new nick>`""")
            return
        else:
            await self.perms_error(ctx)

    # -------------------------------------------------------------#
    # ------------------------ PURGE ------------------------------#
    # -------------------------------------------------------------#

    # Source Code Form:
    # command: https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L1181-L1408
    # Origina Command Licensed under MPL 2.0: https://github.com/Rapptz/RoboDanny/blob/rewrite/LICENSE.txt

    @commands.group(aliases=['purge', 'clear', 'delete', 'clean'], description="""```yaml
    Removes messages that meet a criteria. In order to use this command, you must have Manage Messages permissions.

    Remember that the bot needs Manage Messages as well. These commands cannot be used in a private message.

    When the command is done doing its work, you will get a message detailing which users got removed and how many messages got removed.

    Note: If ran without any sub-commands, it will remove all messages that are NOT pinned to the channel. use "remove all <amount>" to remove everything
    ```
    """)
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def remove(self, ctx, search: typing.Optional[int]):

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
    @commands.has_permissions(manage_messages=True)
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

    # ------------------------------------------------------------#
    # ------------------------ MUTE ------------------------------#
    # ------------------------------------------------------------#
    @commands.command(help="mutes member lol")
    @helpers.is_osp_server()
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to mute')
            return
        muterole = self.bot.get_guild(self.yaml_data['guildID']).get_role(self.yaml_data['MuteRole'])
        if muterole in member.roles:
            await self.error_message(ctx, f'{member} is already muted')
            return
        try:
            await member.add_roles(muterole)
            mem_embed = discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been muted by a moderator", icon_url='https://i.imgur.com/hKNGsMb.png')
            mem_embed.set_image(url='https://i.imgur.com/hXbvCT4.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed = discord.Embed(description=f"""{ctx.author.mention} muted {member.mention} indefinitely...
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed = discord.Embed(description=f"""{ctx.author.mention} muted {member.mention} indefinitely...""",
                                      color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

    # -------------------------------------------------------------#
    # ------------------------ UNMUTE -----------------------------#
    # -------------------------------------------------------------#

    @commands.command(help="unmutes member...")
    @helpers.is_osp_server()
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to unmute')
            return
        muterole = ctx.guild.get_role(self.yaml_data['MuteRole'])
        if muterole not in member.roles:
            await self.error_message(ctx, f'{member} is not muted')
            return
        try:
            await member.remove_roles(muterole)
            mem_embed = discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been unmuted by a moderator", icon_url='https://i.imgur.com/m1MtOVS.png')
            mem_embed.set_image(url='https://i.imgur.com/23XECtg.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed = discord.Embed(description=f"""{ctx.author.mention} unmuted {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed = discord.Embed(description=f"""{ctx.author.mention} unmuted {member.mention}""",
                                      color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

    # -----------------------------------------------------------------#
    # ------------------------ DENYMEDIA ------------------------------#
    # -----------------------------------------------------------------#

    @commands.command(aliases=['nomedia', 'noimages', 'denyimages', 'noimg', 'md', 'mediaban', 'nm', 'mb', 'mban'])
    @helpers.is_osp_server()
    @commands.has_permissions(manage_messages=True)
    async def denymedia(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member to deny media to')
            return
        muterole = self.bot.get_guild(self.yaml_data['guildID']).get_role(self.yaml_data['noMediaRole'])
        if muterole in member.roles:
            await self.error_message(ctx, f'{member} is already in deny media')
            return
        try:
            await member.add_roles(muterole)
            mem_embed = discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been denied permissions to send media by a moderator",
                                 icon_url='https://i.imgur.com/hKNGsMb.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed = discord.Embed(description=f"""{ctx.author.mention} denied media pemrs to {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed = discord.Embed(description=f"""{ctx.author.mention} denied media pemrs to {member.mention}""",
                                      color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

    # -----------------------------------------------------------------#
    # ------------------------ ALLOWMEDIA -----------------------------#
    # -----------------------------------------------------------------#

    @commands.command(
        aliases=['yesmedia', 'yesimages', 'allowimages', 'yesimg', 'ma', 'mediaunban', 'ym', 'mub', 'munban'])
    @helpers.is_osp_server()
    @commands.has_permissions(manage_messages=True)
    async def allowmedia(self, ctx, member: typing.Optional[discord.Member] = None, *, reason=None):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return
        if member == None:
            await self.error_message(ctx, 'You must specify a member deny media to')
            return
        muterole = ctx.guild.get_role(self.yaml_data['noMediaRole'])
        if muterole not in member.roles:
            await self.error_message(ctx, f'{member} is not in deny media')
            return
        try:
            await member.remove_roles(muterole)
            mem_embed = discord.Embed(color=ctx.me.color)
            mem_embed.set_author(name=f"You've been allowed permissions to send media by a moderator",
                                 icon_url='https://i.imgur.com/m1MtOVS.png')
            if reason: mem_embed.set_footer(text=f'reason: {reason}')
            await member.send(embed=mem_embed)
            if reason:
                embed = discord.Embed(description=f"""{ctx.author.mention} returned media pemrs to {member.mention}
```reason: {reason}```""", color=ctx.me.color)
            else:
                embed = discord.Embed(description=f"""{ctx.author.mention} returned media pemrs to {member.mention}""",
                                      color=ctx.me.color)
            await ctx.send(embed=embed)
        except:
            await self.error_message(ctx, 'something went wrong...')

    # ---------------------------------------------------------------#
    # ------------------------ LOCKDOWN -----------------------------#
    # ---------------------------------------------------------------#

    @commands.command(aliases=['lock', 'ld'])
    @commands.has_permissions(manage_messages=True)
    async def lockdown(self, ctx, textchannel: typing.Optional[discord.TextChannel], *, reason=None):

        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        if not textchannel:
            await ctx.message.delete()
            textchannel = ctx.channel
        else:
            await ctx.message.add_reaction('🔓')

        perms = textchannel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = False

        if reason:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms,
                                              reason=f'locked by {ctx.author} - {reason}')
            embed = discord.Embed(
                description=f"{ctx.author.mention} has locked down {textchannel.mention} \n```reason: {reason}```",
                color=ctx.me.color)
        else:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f'locked by {ctx.author}')
            embed = discord.Embed(description=f"{ctx.author.mention} has locked down {textchannel.mention}",
                                  color=ctx.me.color)
        await textchannel.send(embed=embed)

    # -------------------------------------------------------------#
    # ------------------------ UNLOCK -----------------------------#
    # -------------------------------------------------------------#

    @lockdown.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

    @commands.command(aliases=['unlock', 'uld'])
    @commands.has_permissions(manage_messages=True)
    async def unlockdown(self, ctx, textchannel: typing.Optional[discord.TextChannel], *, reason=None):

        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        if not textchannel:
            await ctx.message.delete()
            textchannel = ctx.channel
        else:
            await ctx.message.add_reaction('🔓')

        perms = textchannel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = True

        if reason:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms,
                                              reason=f'unlocked by {ctx.author} - {reason}')
            embed = discord.Embed(
                description=f"{ctx.author.mention} has unlocked {textchannel.mention} \n```reason: {reason}```",
                color=ctx.me.color)
        else:
            await textchannel.set_permissions(ctx.guild.default_role, overwrite=perms,
                                              reason=f'unlocked by {ctx.author}')
            embed = discord.Embed(description=f"{ctx.author.mention} has unlocked {textchannel.mention}",
                                  color=ctx.me.color)
        await textchannel.send(embed=embed)

    @unlockdown.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure): await self.perms_error(ctx)

    # --------------------------------------------------------------------#
    # ------------------------ MOVE MESSAGES -----------------------------#
    # --------------------------------------------------------------------#

    @commands.command(help="moves messages to a different channel")
    @commands.has_permissions(manage_messages=True)
    async def move(self, ctx, amount: typing.Optional[int], channel: typing.Optional[discord.TextChannel]):
        if not any(role in self.staff_roles for role in ctx.author.roles):
            await self.perms_error(ctx)
            return

        # Limitation checking

        if channel == None:
            await self.error_message(ctx, 'you must specify a channel: .move <amount> <#channel>')
            ctx.command.reset_cooldown(ctx)
            return
        elif channel == ctx.channel:
            await self.error_message(ctx, "channel can't be this channel: .move <amount> <#channel>")
            ctx.command.reset_cooldown(ctx)
            return
        if not channel.permissions_for(ctx.guild.me).manage_webhooks and not ctx.channel.permissions_for(
                ctx.me).manage_messages:
            await self.error_message(ctx, 'missing necessary permissions')
            ctx.command.reset_cooldown(ctx)
            return
        if amount == None:
            await self.error_message(ctx, 'you must specify an amount: .move <amount> <#channel>')
            ctx.command.reset_cooldown(ctx)
            return
        elif amount > 20:
            await self.error_message(ctx, 'you can only move 15 messages!')
            ctx.command.reset_cooldown(ctx)
        else:
            try:
                await ctx.message.delete()
            except:
                await ctx.send('missing manage_messages permission', delete_after=5)
                ctx.command.reset_cooldown(ctx)
                return

        # Actual copying and pasting

        history = []
        async for message in ctx.channel.history(limit=amount):
            history.append(message)
            await asyncio.sleep(0.001)
        history.reverse()

        try:
            webhook = await channel.create_webhook(name="DB-Move", reason="created webhook for move command")
        except:
            await ctx.send(f"i'm missing manage_webhooks permission in {channel.mention}", delete_after=5)
            ctx.command.reset_cooldown(ctx)
            return

        for message in history:
            if message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username=message.author.display_name, avatar_url=message.author.display_avatar.url,
                                       file=myfile, content=message.content, embed=embed)
                else:
                    await webhook.send(username=message.author.display_name, avatar_url=message.author.display_avatar.url,
                                       file=myfile, content=message.content)
            else:
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username=message.author.display_name, avatar_url=message.author.display_avatar.url,
                                       content=message.content, embed=embed)
                else:
                    await webhook.send(username=message.author.display_name, avatar_url=message.author.display_avatar.url,
                                       content=message.content)
            try:
                await message.delete()
            except:
                pass
            await asyncio.sleep(0.5)

        await webhook.delete()
        await ctx.send(f'moved {amount} messages to {channel.mention}')


def setup(bot):
    bot.add_cog(moderation(bot))
