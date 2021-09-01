import discord
import typing
from discord.ext import commands

from helpers import helper


def setup(bot):
    bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['userinfo', 'ui', 'whois', 'whoami'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):
        """
        Shows a user's information
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
                f"`{sorted(ctx.guild.members, key=lambda u: u.joined_at).index(u) + 1}`"

        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else:
            boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
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
        Shows a user's guild permissions
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

    @commands.command(help="Shows you information about the server")
    @commands.is_owner()
    async def si(self, ctx):
        guild = ctx.guild
        enabled_features = []
        disabled_features = []
        features = set(guild.features)
        all_features = {
            'PARTNERED': 'Partnered',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Server Discovery',
            'COMMUNITY': 'Community Server',
            'FEATURABLE': 'Featured',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'INVITE_SPLASH': 'Invite Splash',
            'VIP_REGIONS': 'VIP Voice Servers',
            'VANITY_URL': 'Vanity Invite Url',
            'COMMERCE': 'Commerce',
            'LURKABLE': 'Lurkable',
            'NEWS': 'News Channels',
            'ANIMATED_ICON': 'Animated Icon',
            'BANNER': 'Banner',
        }
        all_features2 = {
            'ANIMATED_ICON': 'Animated Server Icon',
            'BANNER': 'Server Banner',
            'COMMERCE': 'Commerce',
            'COMMUNITY': 'Community Server',
            'DISCOVERABLE': 'Discoverable',
            'FEATURABLE': 'Featured',
            'INVITE_SPLASH': 'Invite Splash',
            'MEMBER_VERIFICATION_GATE_ENABLED': 'Membership Screening',
            'MONETIZATION_ENABLED': 'Monetization',
            'MORE_EMOJI': 'More Emoji',
            'MORE_STICKERS': 'More Stickers',
            'NEWS': 'News Channels',
            'PARTNERED': 'Partnered',
            'PREVIEW_ENABLED': 'Preview Enabled',
            'PRIVATE_THREADS': 'Private Threads',
            'THREE_DAY_THREAD_ARCHIVE': '3 Day Thread Archive',
            'SEVEN_DAY_THREAD_ARCHIVE': '1 Week Thread Archive',
            'TICKETED_EVENTS_ENABLED': 'Ticketed Events',
            'VANITY_URL': 'Vanity Invite URL',
            'VERIFIED': 'Verified',
            'VIP_REGIONS': 'VIP Voice Regions',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen'
        }

        for feature, label in all_features.items():
            if feature in features:
                enabled_features.append(f'{ctx.tick(True)} {label}')
            else:
                disabled_features.append(f'{ctx.tick(None)} {label}')

        embed = discord.Embed(color=discord.Colour.blurple(),
                              title=ctx.guild.name,
                              description=f"**Server ID:** {ctx.guild.id}"
                                          f"\n**Owner** {ctx.guild.owner} ({ctx.guild.owner.id})")

        embed.add_field(name="<:rich_presence:658538493521166336> Features",
                        value='\n'.join(enabled_features+disabled_features))

        await ctx.send(embed=embed)

        return

        server = ctx.guild
        if ctx.me.guild_permissions.ban_members:
            bans = len(await server.bans())
        else:
            bans = None
        embed = discord.Embed(title=f"Server info - {server}", description=f"""
Name: {server}
<:greyTick:860644729933791283> ID: {server.id}
<:members:658538493470965787> Members: {len(server.members)} (:robot: {len([m for m in server.members if not m.bot])})
:robot: Bots: {len([m for m in server.members if not m.bot])}
<:owner_crown:845946530452209734> Owner: {server.owner}
Created: {discord.utils.format_dt(server.created_at, style="f")} ({discord.utils.format_dt(server.created_at, style='R')})
Region: {server.region}
<:members:858326990725709854> Max members: {server.max_members}
<:bans:878324391958679592> Banned members: {bans or "missing permissions"}
<:status_offline:596576752013279242> Statuses: <:status_online:596576749790429200> 4151 <:status_idle:596576773488115722> 3213 <:status_dnd:596576774364856321> 3307 <:status_streaming:596576747294818305> 0 <:status_offline:596576752013279242> 27186
<:text_channel:876503902554578984> Channels: <:text_channel:876503902554578984> {len(server.text_channels)} <:voice_channel:876503909512933396> {len(server.voice_channels)}
:sunglasses: Animated emojis: {len([x for x in server.emojis if x.animated])}/{server.emoji_limit}
:sunglasses: Non animated emojis: {len([x for x in server.emojis if not x.animated])}/{server.emoji_limit}
<:boost:858326699234164756> Level: {server.premium_tier}
<:boost:858326699234164756> Boosts: {server.premium_subscription_count}
        """)
        await ctx.send(embed=embed)

