import contextlib
import contextlib
import io
import random
import typing
from itertools import cycle

import aiohttp
import discord
from discord.ext import commands

from bot import CustomContext
from helpers import constants
from helpers import helper
from ._base import UtilityBase


class UserInfoView(discord.ui.View):
    def __init__(
        self, ctx: CustomContext, uinfo_embed: discord.Embed, banner: discord.Embed = None, order_embed: discord.Embed = None
    ):
        super().__init__()
        if banner:
            self.embeds = cycle([uinfo_embed, order_embed, banner])
            self.labels = cycle(['Show Banner', 'Show User Info', 'Show Join Order'])
        else:
            self.embeds = cycle([uinfo_embed, order_embed])
            self.labels = cycle(['Show User Info', 'Show Join Order'])
        self.banner = banner
        self.ui = uinfo_embed
        self.message: discord.Message = None
        self.ctx = ctx

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.defer()
        return False

    async def start(self):
        self.message = await self.ctx.send(embed=next(self.embeds), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji='🔁', label='Show Join Order')
    async def next_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = next(self.embeds)
        button.label = next(self.labels)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.red, emoji='🗑')
    async def stop_button(self, _, __):
        with contextlib.suppress(discord.HTTPException):
            await self.message.delete()
            await self.ctx.message.add_reaction(random.choice(constants.DONE))
        self.stop()


class UserInfo(UtilityBase):
    @commands.command(aliases=['uinfo', 'ui', 'whois', 'userinfo'], name='user-info')
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def userinfo(self, ctx: CustomContext, *, member: discord.Member = commands.Author):
        """
        Shows a user's information. If not specified, shows your own.
        """
        fetched_user = await self.bot.fetch_user(member.id)

        embed = discord.Embed(color=member.color if member.color not in (None, discord.Color.default()) else ctx.color)
        embed.set_author(name=f"{member}'s User Info", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name=f"{constants.INFORMATION_SOURCE} General information",
            value=f"**ID:** {member.id}"
            f"\n**Name:** {member.name}"
            f"\n╰ **Nick:** {(member.nick or '✖')}"
            f"\n**Profile Color:** {str(fetched_user.accent_color).upper() or 'Not set'}"
            f"\n**Owner:** {ctx.tick(member == member.guild.owner)} • "
            f"**Bot:** {ctx.tick(member.bot)}",
            inline=True,
        )

        embed.add_field(
            name=f"{constants.STORE_TAG} Badges",
            value=helper.get_user_badges(user=member, fetched_user=fetched_user, bot=self.bot) or "No Badges",
            inline=True,
        )

        embed.add_field(
            name=f"{constants.INVITE} Created At",
            value=f"╰ {discord.utils.format_dt(member.created_at, style='f')} "
            f"({discord.utils.format_dt(member.created_at, style='R')})",
            inline=False,
        )

        try:
            pos = sorted(ctx.guild.members, key=lambda m: m.joined_at or m.created_at).index(member) + 1
        except ValueError:
            pos = "Error."
            if not member.guild.chunked:
                self.bot.loop.create_task(member.guild.chunk())

        embed.add_field(
            name=f"{constants.JOINED_SERVER} Joined At",
            value=(
                f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                f"({discord.utils.format_dt(member.joined_at, style='R')})"
                f"\n\u200b \u200b \u200b \u200b ╰ {constants.MOVED_CHANNELS} **Join Position:** {pos}"
            )
            if member.joined_at
            else "Could not get data",
            inline=False,
        )

        if member.premium_since:
            embed.add_field(
                name=f"{constants.BOOST} Boosting since:",
                value=f"╰ {discord.utils.format_dt(member.premium_since, style='f')} "
                f"({discord.utils.format_dt(member.premium_since, style='R')})",
                inline=False,
            )

        custom_activity = discord.utils.find(lambda act: isinstance(act, discord.CustomActivity), member.activities)
        activity_string = (
            f"`{discord.utils.remove_markdown(custom_activity.name)}`"
            if custom_activity and custom_activity.name
            else 'User has no custom status.'
        )
        embed.add_field(
            name=f'Activity:',
            value=f"\n{helper.generate_user_statuses(member)}" f"\n**Custom status:**" f"\n{activity_string}",
        )

        spotify = discord.utils.find(lambda act: isinstance(act, discord.Spotify), member.activities)

        ack = await self.bot.db.fetchval("SELECT description FROM ack WHERE user_id = $1", member.id)

        embed.add_field(
            name=f"{constants.SPOTIFY} Spotify:",
            value=(
                f"**[{spotify.title}]({spotify.track_url})**"
                f"\nBy __{spotify.artist}__"
                f"\nOn __{spotify.album}__"
                f"\n**Time:** {helper.deltaconv((ctx.message.created_at - spotify.start).total_seconds())}/"
                f"{helper.deltaconv(spotify.duration.total_seconds())}"
                if spotify
                else 'Not listening to anything...'
            )
            + (f'\n\n⭐ **Acknowledgements:**\n{ack}' if ack else ''),
        )

        perms = helper.get_perms(member.guild_permissions)
        if perms:
            embed.add_field(name=f"{constants.STORE_TAG} Staff Perms:", value=f"`{'` `'.join(perms)}`", inline=False)

        roles = [r.mention for r in member.roles if not r.is_default()]
        roles.reverse()
        if roles:
            embed.add_field(
                name=f"{constants.ROLES_ICON} Roles:",
                value=", ".join(roles) + f"\n**Top Role:** {member.top_role} • "
                f"**Color:** {member.color if member.color is not discord.Color.default() else 'Default'}",
                inline=False,
            )

        order_embed = discord.Embed(
            color=member.color if member.color not in (None, discord.Color.default()) else ctx.color,
            timestamp=ctx.message.created_at,
        )
        order_embed.set_author(name=f"{member}'s Joined order", icon_url=member.display_avatar.url)
        order_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        sort_mems = sorted(ctx.guild.members, key=lambda m: m.joined_at or m.created_at)
        index = sort_mems.index(member)
        members = [
            f'{m} ({m.joined_at.strftime("%d %b %Y. %S:%H")})'
            for m in sort_mems[(index - 10 if index > 10 else 0) : index + 10]
        ]
        join_order = '\n'.join(
            [
                f"{n}.{' ' * (10 - len(str(n)) + 1)}{s}"
                for n, s in enumerate(members, start=(index - 10 if index > 10 else 0) + 1)
            ]
        ).replace(f"  {member}", f"> {member}")
        order_embed.description = '```py\n' + join_order + '\n```'
        order_embed.add_field(
            name=f"{constants.JOINED_SERVER} Joined At",
            value=(
                f"╰ {discord.utils.format_dt(member.joined_at, style='f')} "
                f"({discord.utils.format_dt(member.joined_at, style='R')})"
                f"\n\u200b \u200b \u200b \u200b ╰ {constants.MOVED_CHANNELS} **Join Position:** "
                f"{sorted(ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()).index(member) + 1}"
            )
            if member.joined_at
            else "This user's joined data seems to be None, so ive put them near the end,",
            inline=False,
        )

        banner_embed = None
        if fetched_user.banner:
            banner_embed = discord.Embed(
                color=member.color if member.color not in (None, discord.Color.default()) else ctx.color,
                timestamp=ctx.message.created_at,
            )
            banner_embed.set_author(name=f"{member}'s Banner", icon_url=member.display_avatar.url)
            banner_embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            banner_embed.set_image(url=fetched_user.banner.url)
        view = UserInfoView(ctx, embed, banner_embed, order_embed)
        await view.start()

    @commands.command(aliases=['av', 'pfp'])
    async def avatar(self, ctx: CustomContext, *, member: typing.Union[discord.Member, discord.User] = None):
        """
        Displays a user's avatar. If not specified, shows your own.
        """
        user: discord.User = member or ctx.author
        embed = discord.Embed(title=user, url=user.display_avatar.url)
        if ctx.guild and isinstance(user, discord.Member) and user.guild_avatar:
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.description = (
                f"[avatar]({user.avatar.url if user.avatar else user.default_avatar.url}) | "
                f"[server avatar]({user.display_avatar.url})"
            )
        embed.set_image(url=user.display_avatar.url)

        await ctx.send(embed=embed, footer=False)

    @commands.command()
    async def spotify(self, ctx, member: discord.Member = None):
        """Get the spotify link of a member"""
        try:
            async with ctx.typing():
                member = member or ctx.author
                spotify: discord.Spotify = discord.utils.find(lambda a: isinstance(a, discord.Spotify), member.activities)
                if spotify is None:
                    return await ctx.send(f"**{member}** is not listening or connected to Spotify.")
                params = {
                    'title': spotify.title,
                    'cover_url': spotify.album_cover_url,
                    'duration_seconds': spotify.duration.seconds,
                    'start_timestamp': spotify.start.timestamp(),
                    'artists': spotify.artists,
                }

                async with self.bot.session.get('https://api.jeyy.xyz/discord/spotify', params=params) as response:
                    buf = io.BytesIO(await response.read())
                artists = ', '.join(spotify.artists)
                file = discord.File(buf, 'spotify.png')
                embed = discord.Embed(description=f"**{spotify.title}** by **{artists}**")
                embed.set_author(name=f"{member}'s Spotify", icon_url=member.display_avatar.url)
                embed.set_image(url='attachment://spotify.png')
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(emoji=constants.SPOTIFY, url=spotify.track_url, label='Listen to this track')
                )
            await ctx.send(embed=embed, file=file, view=view)
        except aiohttp.ClientConnectorCertificateError:
            await ctx.send("⚠ **|** SSL certificate thing stupid!! Use DuckBot at `db.spotify`")
