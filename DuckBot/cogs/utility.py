import asyncio
import re
import typing
import unicodedata
import discord

from inspect import Parameter
from typing import Optional
from discord.ext import commands, menus

import errors
from helpers import helper


def setup(bot):
    bot.add_cog(Utility(bot))


class EmbedPageSource(menus.ListPageSource):

    async def format_page(self, menu, item):
        embed = discord.Embed(description="\n".join(item), title="ℹ Character information")
        return embed


class Utility(commands.Cog):
    """
    💬 Text and utility commands, mostly to display information about a server.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='charinfo')
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def character_info(self, ctx: commands.Context, *, characters: str):
        """Shows you information about a number of characters."""

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - **{c}** \N{EM DASH} ' \
                   f'<http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))

        menu = menus.MenuPages(EmbedPageSource(msg.split("\n"), per_page=20), delete_message_after=True)
        await menu.start(ctx)

    # .s <text>
    # resends the message as the bot

    @commands.command(aliases=['s', 'send'],
                      help="Speak as if you were me. # URLs/Invites not allowed!")
    @commands.check_any(commands.bot_has_permissions(send_messages=True), commands.is_owner())
    async def say(self, ctx: commands.context, *, msg: str) -> Optional[discord.Message]:

        results = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+",
                             msg)  # HTTP/HTTPS URL regex
        results2 = re.findall(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?",
                              msg)  # Discord invite regex
        if results or results2:
            await ctx.send(
                f"hey, {ctx.author.mention}. Urls or invites aren't allowed!",
                delete_after=10)
            return await ctx.message.delete(delay=10)

        await ctx.message.delete(delay=0)
        if ctx.channel.permissions_for(ctx.author).manage_messages:
            allowed = True
        else:
            allowed = False

        return await ctx.send(msg[0:2000], allowed_mentions=discord.AllowedMentions(everyone=False,
                                                                                    roles=False,
                                                                                    users=allowed),
                              reference=ctx.message.reference,
                              reply=False)

    # .a <TextChannel> <text>
    # sends the message in a channel

    @commands.command(
        aliases=['a', 'an', 'announce'],
        usage="<channel> <message_or_reply>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def echo(self, ctx: commands.Context, channel: typing.Union[discord.TextChannel, int], *,
                   message_or_reply: str = None) \
            -> discord.Message:
        """"Echoes a message to another channel"""
        if isinstance(channel, int):
            channel = self.bot.get_channel(channel)
        if not ctx.message.reference and not message_or_reply:
            raise commands.MissingRequiredArgument(
                Parameter(name='message_or_reply', kind=Parameter.POSITIONAL_ONLY))
        elif ctx.message.reference:
            message_or_reply = ctx.message.reference.resolved
        return await channel.send(message_or_reply[0:2000], allowed_mentions=discord.AllowedMentions(everyone=False,
                                                                                                     roles=False,
                                                                                                     users=True))

    @commands.command(
        aliases=['e', 'edit'],
        usage="[new message] [--d|--s]")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def edit_message(self, ctx, *, new: typing.Optional[str] = '--d'):
        """Quote a bot message to edit it.
        # Append --s at the end to suppress embeds and --d to delete the message
        """
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            if new.endswith("--s"):
                await msg.edit(content=f"{new[:-3]}", suppress=True)
            elif new.endswith('--d'):
                await msg.delete()
            else:
                await msg.edit(content=new, suppress=False)
            await ctx.message.delete(delay=0.1)
        else:
            raise errors.NoQuotedMessage

    @commands.command(aliases=['uinfo', 'ui', 'whois', 'whoami'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, member: typing.Optional[discord.Member]):
        """
        Shows a user's information. If not specified, shows your own.
        """
        member = member or ctx.author

        embed = discord.Embed(color=(member.color if member.color != discord.Colour.default() else ctx.me.color))
        embed.set_author(name=member, icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="<:info:860295406349058068> General information",
                        value=
                        f"**ID:** {member.id}"
                        f"\n**Name:** {member.name}"
                        f"\n╰ **Nick:** {(member.nick or '✖')}"
                        f"\n**Owner:** {ctx.tick(member == member.guild.owner)} • "
                        f"**Bot:** {ctx.tick(member.bot)}", inline=True)

        embed.add_field(name="<:store_tag:658538492409806849> Badges",
                        value=(helper.get_user_badges(member) or "No Badges"), inline=True)

        embed.add_field(name="<:invite:860644752281436171> Created At",
                        value=f"╰ {discord.utils.format_dt(member.created_at, style='f')} "
                              f"({discord.utils.format_dt(member.created_at, style='R')})",
                        inline=False)

        embed.add_field(name="<:joined:849392863557189633> Created At",
                        value=(f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                               f"({discord.utils.format_dt(member.joined_at, style='R')})"
                               f"\n\u200b \u200b \u200b \u200b ╰ <:moved:848312880666640394> **Join Position:** "
                               f"{sorted(ctx.guild.members, key=lambda member: member.joined_at).index(member) + 1}")
                        if member else "Could not get data",
                        inline=False)

        perms = helper.get_perms(member.guild_permissions)
        if perms:
            embed.add_field(name="<:store_tag:658538492409806849> Staff Perms",
                            value=f"`{'` `'.join(perms)}`", inline=False)

        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        if roles:
            embed.add_field(name="<:role:808826577785716756>**Roles:** Roles",
                            value=" ".join(roles), inline=False)

        if member.premium_since:
            embed.add_field(name="<:booster4:860644548887969832> Boosting since:",
                            value=f"╰ {discord.utils.format_dt(member.premium_since, style='f')} "
                                  f"({discord.utils.format_dt(member.premium_since, style='R')})",
                            inline=False)

        return await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def old_userinfo(self, ctx, user: typing.Optional[discord.Member]):
        """
        Shows a user's information. If not specified, shows your own.
        """
        user = user or ctx.author
        # BADGES
        badges = helper.get_user_badges(user)
        if badges:
            badges = f"\n<:store_tag:658538492409806849>**Badges:**{badges}"
        else:
            badges = ''
        # BADGES
        perms = helper.get_perms(user.guild_permissions)
        if perms:
            perms = f"\n<:store_tag:658538492409806849>**Staff permissions:** {', '.join(perms)}"
        else:
            perms = ''
        # USERID
        userid = f"\n<:greyTick:596576672900186113>**ID:** `{user.id}`"
        # NICKNAME
        if user.nick:
            nick = f"\n<:nickname:850914031953903626>**Nickname:** `{user.nick}`"
        else:
            nick = ""
        # CREATION DATE
        date = f"<t:{round(user.created_at.timestamp())}:F>"
        rounded_date = f"<t:{round(user.created_at.timestamp())}:R>"
        created = f"\n<:invite:860644752281436171>**Created:** {date} ({rounded_date})"
        # JOIN DATE
        if user.joined_at:
            date = f"<t:{round(user.joined_at.timestamp())}:F>"
            rounded_date = f"<t:{round(user.joined_at.timestamp())}:R>"
            joined = f"\n<:joined:849392863557189633>**joined:** {date} ({rounded_date})"
        else:
            joined = ""
        # GUILD OWNER
        if user is ctx.guild.owner:
            owner = f"\n<:owner:585789630800986114>**Owner:** <:check:314349398811475968>"
        else:
            owner = ""
        # BOT
        if user.bot:
            bot = f"\n<:botTag:230105988211015680>**Bot:** <:check:314349398811475968>"
        else:
            bot = ""
        # Join Order
        order = f"\n<:moved:848312880666640394>**Join position:** " \
                f"`{sorted(ctx.guild.members, key=lambda user: user.joined_at).index(user) + 1}`"

        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else:
            boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role:
                continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"\n<:role:808826577785716756>**Roles:** {roles}"
        # EMBED
        embed = discord.Embed(color=ctx.me.color,
                              description=f"{badges}{owner}{bot}{userid}{created}{nick}{joined}{order}{boost}{roles}{perms}")
        embed.set_author(name=user, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['perms'])
    @commands.guild_only()
    async def permissions(self, ctx: commands.Context, target: discord.Member = None) -> discord.Message:
        """
        Shows a user's guild permissions.
        Note: This does not take into account channel overwrites.
        """
        target = target or ctx.me
        allowed = []
        denied = []
        for perm in target.guild_permissions:
            if perm[1] is True:
                allowed.append(ctx.default_tick(perm[1], perm[0].replace('_', ' ').replace('guild', 'server')))
            elif perm[1] is False:
                denied.append(ctx.default_tick(perm[1], perm[0].replace('_', ' ').replace('guild', 'server')))

        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(icon_url=target.display_avatar.url, name=target)
        embed.set_footer(icon_url=target.display_avatar.url, text=f"{target.name}'s guild permissions")
        if allowed:
            embed.add_field(name="allowed", value="\n".join(allowed))
        if denied:
            embed.add_field(name="denied", value="\n".join(denied))
        return await ctx.send(embed=embed)

    @commands.command(aliases=["si"])
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context, guild_id: int = None):
        """
        Shows the current server's information.
        """
        if guild_id and await self.bot.is_owner(ctx.author):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return await ctx.send(f'Invalid Guild ID given.')
        else:
            guild = ctx.guild

        enabled_features = []
        features = set(guild.features)
        all_features = {
            'COMMUNITY': 'Community Server',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Discoverable',
            'PARTNERED': 'Partnered',
            'FEATURABLE': 'Featured',
            'COMMERCE': 'Commerce',
            'MONETIZATION_ENABLED': 'Monetization',
            'NEWS': 'News Channels',
            'PREVIEW_ENABLED': 'Preview Enabled',
            'INVITE_SPLASH': 'Invite Splash',
            'VANITY_URL': 'Vanity Invite URL',
            'ANIMATED_ICON': 'Animated Server Icon',
            'BANNER': 'Server Banner',
            'MORE_EMOJI': 'More Emoji',
            'MORE_STICKERS': 'More Stickers',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'MEMBER_VERIFICATION_GATE_ENABLED': 'Membership Screening',
            'TICKETED_EVENTS_ENABLED': 'Ticketed Events',
            'VIP_REGIONS': 'VIP Voice Regions',
            'PRIVATE_THREADS': 'Private Threads',
            'THREE_DAY_THREAD_ARCHIVE': '3 Day Thread Archive',
            'SEVEN_DAY_THREAD_ARCHIVE': '1 Week Thread Archive',
        }
        boosting_level_emojis = {
            '0': '<:Level0_guild:883081706918252604>',
            '1': '<:Level1_guild:883072977430794240>',
            '2': '<:Level2_guild:883073003984916491>',
            '3': '<:Level3_guild:883073034817245234>'
        }

        for feature, label in all_features.items():
            if feature in features:
                enabled_features.append(f'{ctx.tick(True)} {label}')

        embed = discord.Embed(color=discord.Colour.blurple(),
                              title=guild.name)

        embed.add_field(name="<:rich_presence:658538493521166336> Features:",
                        value='\n'.join(enabled_features), inline=True)

        embed.add_field(name="<:info:860295406349058068> General Info:",
                        value=f"🆔 {guild.id}"
                              f"\n<:owner_crown:845946530452209734> {guild.owner}"
                              f"\n👤 {len([m for m in guild.members if not m.bot])} "
                              f"(🤖 {len([m for m in guild.members if m.bot])})"
                              f"\n╰ ➕ {guild.member_count}/{guild.max_members}"
                              f"\n🌐 Server Region: {helper.get_server_region(guild)}"
                              f"\n<:role:860644904048132137> Roles: {len(guild.roles)}")

        if guild.description:
            desc = guild.description
        else:
            desc = "<:toggle_off:857842924544065536> Feature toggled off." \
                   "\nEnable it in `community -> overview` in server settings!"

        embed.add_field(name="<:info:860295406349058068> Server description:",
                        value=desc, inline=False)

        embed.add_field(name="<:rich_presence:658538493521166336> Channels:",
                        value=f"<:voice:860330111377866774> {len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}"
                              f"\n<:view_channel:854786097023549491> Channels: {len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}"
                              f"\n<:category:882685952999428107> Categories: {len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}"
                              f"\n<:stagechannel:824240882793447444> Stages: {len([c for c in guild.channels if isinstance(c, discord.StageChannel)])}"
                              f"\n<:threadnew:833432474347372564> Threads: {len(guild.threads)}"
                              f"\n╰ (visible by me)",
                        inline=True)

        embed.add_field(name="<:emoji_ghost:658538492321595393> Emojis:",
                        value=f"Static: {len([e for e in guild.emojis if not e.animated])}/{guild.emoji_limit} "
                              f"\nAnimated: {len([e for e in guild.emojis if e.animated])}/{guild.emoji_limit} ",
                        inline=True)

        last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
        if last_boost.premium_since is not None:
            boost = f"\n{last_boost}" \
                    f"\n╰ {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "\n╰ No active boosters"

        embed.add_field(name="<:booster4:860644548887969832> Boosts:",
                        value=f"{boosting_level_emojis[str(guild.premium_tier)]} Level: {guild.premium_tier}"
                              f"\n╰ Amount: {guild.premium_subscription_count}"
                              f"\n**<:booster4:860644548887969832> Last booster:**{boost}")

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        """
        Displays a user's avatar. If not specified, shows your own.
        """
        user: discord.Member = user or ctx.author
        embed = discord.Embed(color=discord.Colour.blurple(),
                              title=user, url=user.display_avatar.url)
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed, footer=False)

    @commands.group(invoke_without_command=True, aliases=['em'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def emoji(self, ctx, custom_emojis: commands.Greedy[discord.PartialEmoji]):
        """
        Makes an emoji bigger and shows it's formatting
        """

        if not custom_emojis:
            raise commands.MissingRequiredArgument(
                Parameter(name='custom_emojis', kind=Parameter.POSITIONAL_ONLY))

        if len(custom_emojis) > 5:
            raise commands.TooManyArguments()

        for emoji in custom_emojis:
            if emoji.animated:
                emoticon = f"*`<`*`a:{emoji.name}:{emoji.id}>`"
            else:
                emoticon = f"*`<`*`:{emoji.name}:{emoji.id}>`"
            embed = discord.Embed(description=f"{emoticon}", color=ctx.me.color)
            embed.set_image(url=emoji.url)
            await ctx.send(embed=embed)

    @emoji.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_lock(self, ctx: commands.Context, server_emoji: discord.Emoji,
                         roles: commands.Greedy[discord.Role]) -> discord.Message:
        """
        Locks an emoji to one or multiple roles. Input as many roles as you want in the "[roles]..." parameter.
        Note: admin/owner DOES NOT bypass this lock, so be sure to have the role if you wish to unlock the emoji.
        # If the role is removed and re-assigned, the locked emoji will not be visible until you restart your client.
        """
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        embed = discord.Embed(color=ctx.me.color,
                              description=f"**Restricted access of {server_emoji} to:**"
                                          f"\n{', '.join([r.mention for r in roles])}"
                                          f"\nTo unlock the emoji do `{ctx.clean_prefix} emoji unlock {server_emoji}`"
                                          f"_Note that to do this you will need one of the roles the emoji has been "
                                          f"restricted to. \nNo, admin permissions don't bypass this lock._")
        embed.set_footer()
        await ctx.send(embed=embed)
        await server_emoji.edit(roles=roles)

    @emoji.group(name="unlock", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock(self, ctx: commands.Context, server_emoji: discord.Emoji) -> discord.Message:
        """
        Unlocks a locked emoji.
        """
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        await server_emoji.edit(roles=[])
        embed = discord.Embed(color=ctx.me.color,
                              title="Successfully unlocked emoji!",
                              description=f"**Allowed {server_emoji} to @everyone**")
        return await ctx.send(embed=embed)

    @emoji_unlock.command(name="all")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock_all(self, ctx: commands.Context):
        """
        Unlocks all locked emojis in the current server.
        """
        async with ctx.typing():
            unlocked = []
            for emoji in ctx.guild.emojis:
                if emoji.roles:
                    await emoji.edit(roles=[], reason=f"Unlock all emoji requested by {ctx.author} ({ctx.author.id})")
                    unlocked.append(emoji)
                    await asyncio.sleep(1)
            await ctx.send(f"Done! Unlocked {len(unlocked)} emoji(s)"
                           f"\n {' '.join([str(em) for em in unlocked])}")

    @emoji.command(name="steal", hidden=True, aliases=['s'])
    @commands.is_owner()
    async def emoji_steal(self, ctx, index: int = 1):
        if not ctx.message.reference:
            raise errors.NoQuotedMessage

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
        emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
        if not emojis:
            raise errors.NoEmojisFound

        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
        except IndexError:
            return await ctx.send(f"Emoji out of index {index}/{len(emojis)}!"
                                  f"\nIndex must be lower or equal to {len(emojis)}")
        file = await emoji.read()
        guild = self.bot.get_guild(831313673351593994)
        emoji = await guild.create_custom_emoji(name=emoji.name, image=file, reason="stolen emoji KEK")
        try:
            await ctx.message.add_reaction(emoji)
        except discord.NotFound:
            pass

    @emoji.command(name="clone")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_clone(self, ctx: commands.Context,
                          server_emoji: typing.Optional[typing.Union[discord.Embed,
                                                                     discord.PartialEmoji]],
                          index: int = 1):
        """
        Clones an emoji into the current server.
        # To steal an emoji from someone else, quote their message to grab the emojis from there.
        # If the quoted message has multiple emojis, input an index number to specify the emoji, for example, doing "%PRE%emoji 5" will steal the 5th emoji from the message.
        None: Index is only for when stealing emojis from other people.
        """
        if ctx.message.reference:
            custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
            emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
            if not emojis:
                raise errors.NoEmojisFound
            try:
                server_emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
            except IndexError:
                return await ctx.send(f"Emoji out of index {index}/{len(emojis)}!"
                                      f"\nIndex must be lower or equal to {len(emojis)}")

        if not server_emoji:
            raise commands.MissingRequiredArgument(
                Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))

        file = await server_emoji.read()
        guild = ctx.guild
        server_emoji = await guild.create_custom_emoji(name=server_emoji.name, image=file,
                                                       reason=f"Cloned emoji, requested by {ctx.author}")
        await ctx.send(f"Done! cloned {server_emoji}")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def minecraft_uuid(self, ctx: commands.Context, *, username: str) \
            -> typing.Optional[discord.Message]:
        """
        Fetches the UUID of a minecraft user from the mojang API
        """
        argument = username
        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
            embed = discord.Embed(color=ctx.me.color)
            if cs.status == 204:
                embed.add_field(name='⚠ ERROR ⚠', value=f"`{argument}` is not a minecraft username!")

            elif cs.status == 400:
                embed.add_field(name="⛔ ERROR ⛔", value="ERROR 400! Bad request.")
            else:
                res = await cs.json()
                user = res["name"]
                uuid = res["id"]
                embed.add_field(name=f'Minecraft username: `{user}`', value=f"**UUID:** `{uuid}`")
            return await ctx.send(embed=embed)

    @commands.command(name="commands")
    async def _commands(self, ctx: commands.Context) -> discord.Message:
        """
        Shows all the bot commands, even the ones you can't run.
        """

        ignored_cogs = ("Bot Management", "Jishaku")

        def divide_chunks(str_list, n):
            for i in range(0, len(str_list), n):
                yield str_list[i:i + n]

        shown_commands = [c.name for c in self.bot.commands if c.cog_name not in ignored_cogs]
        ml = max([len(c.name) for c in self.bot.commands if c.cog_name not in ignored_cogs])

        all_commands = list(divide_chunks(shown_commands, 3))
        all_commands = '\n'.join([''.join([f"{x}{' ' * (ml - len(x))}" for x in c]).strip() for c in all_commands])

        return await ctx.send(embed=discord.Embed(color=ctx.me.color,
                                                  title=f"Here are ALL my commands ({len(shown_commands)})",
                                                  description=f"```fix\n{all_commands}\n```"))
