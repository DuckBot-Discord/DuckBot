import discord
import random
from discord.ext import commands


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """🧪 Test commands. 💀 May not work or not be what you think they'll be."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows you information about the server")
    @commands.is_owner()
    async def si(self, ctx):
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

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def mute(self, ctx: commands.Context, member: discord.Member, reason: str):
        reason = reason or "No reason given"
        reason = f"Mute by {ctx.author} ({ctx.author.id}): {reason}"
        if not ctx.author == ctx.guild.owner or \
                ctx.author.top_role > member.top_role:
            return await ctx.send("You're not high enough in role hierarchy to mute that member.")
        mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        if not mute_role:
            return await ctx.send("You don't have a mute role assigned!"
                                  "\n create one with the `muterole add` command")

        role = ctx.guild.get_role(int(mute_role))
        if not isinstance(role, discord.Role):
            return await ctx.send("The muted role seems to have been deleted!"
                                  "\nRe-assign it with the `muterole add` command")

        if role > ctx.me.top_role:
            return await ctx.send("I'm not high enough in role hierarchy to assign that role.")

        try:
            await member.add_roles(role)
        except discord.Forbidden:
            return await ctx.send(f"I don't seem to have permissions to add the `{role.name}` role")

        await ctx.send("<:shut:744345896912945214>👌")

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def muterole(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:

            mute_role = await self.bot.db.fetchval('SELECT muted_id FROM prefixes WHERE guild_id = $1', ctx.guild.id)

            if not mute_role:
                return await ctx.send("You don't have a mute role assigned!"
                                      "\n create one with the `muterole add` command")

            role = ctx.guild.get_role(int(mute_role))
            if not isinstance(role, discord.Role):
                return await ctx.send("The muted role seems to have been deleted!"
                                      "\nRe-assign it with the `muterole add` command")

            return await ctx.send(f"This guild's mute role is {role.mention}",
                                  allowed_mentions=discord.AllowedMentions().none())

    @muterole.command(name="add")
    async def muterole_add(self, ctx: commands.Context, role: discord.Role):
        await self.bot.db.execute("INSERT INTO prefixes(guild_id, muted_id) VALUES ($1, $2) "
                                  "ON CONFLICT (guild_id, muted_id) "
                                  "DO UPDATE SET guild_id = $1, muted_id = $2", ctx.guild.id, role.id)

        return await ctx.send(f"This guild's mute role is {role.mention}",
                              allowed_mentions=discord.AllowedMentions().none())
