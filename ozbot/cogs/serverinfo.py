import typing, discord, asyncio
from discord.ext import commands
import json
from discord.ext.commands.cooldowns import BucketType

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['si', 'sinfo'])
    @commands.cooldown(1, 20.0, commands.BucketType.user)
    async def serverinfo(self, ctx, argument = "no"):

        embed = discord.Embed(title="ℹ OZ server information", color=ctx.me.color)


        # OZ

        user = ctx.guild.get_member(799749818062077962)
        if user.status == discord.Status.online:

            act = json.loads(user.activities[0].name.replace("'", "\""))

            embed.add_field(name="Survival", value=f"tps: {act['tps']} | online players: {act['pl']}", inline=False)

        else:

            embed.add_field(name="Survival", value="server offline", inline=False)

        # SKYBLOCK

        if ctx.channel.permissions_for(ctx.author).manage_messages:
            user = ctx.guild.get_member(755309062555435070)
            if user.status == discord.Status.online:

                act = json.loads(user.activities[0].name.replace("'", "\""))

                embed.add_field(name="Skyblock", value=f"tps: {act['tps']} | online players: {act['pl']}", inline=False)

        else:

            embed.add_field(name="Skyblock", value="server offline", inline=False)

        # CREATIVE

        if ctx.channel.permissions_for(ctx.author).manage_messages:
            user = ctx.guild.get_member(764623648132300811)
            if user.status == discord.Status.online:

                act = json.loads(user.activities[0].name.replace("'", "\""))

                embed.add_field(name="Creative", value=f"tps: {act['tps']} | online players: {act['pl']}", inline=False)

        else:

            embed.add_field(name="Creative", value="server offline", inline=False)

            # CLOUDKEEP

        user = ctx.guild.get_member(755302239794626580)
        if user.status == discord.Status.online:

            act = json.loads(user.activities[0].name.replace("'", "\""))

            embed.add_field(name="Old cloudkeep", value=f"tps: {act['tps']} | online players: {act['pl']}", inline=False)

        else:

            embed.add_field(name="Old Cloudkeep", value="server offline", inline=False)

        await ctx.send(embed=embed)

    @serverinfo.error
    async def serverinfo_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            err = f'{error}'
            await ctx.send(err.replace("discord.ext.commands.errors.CommandOnCooldown:", " "), delete_after=5)
            await asyncio.sleep (5)
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(help(bot))
