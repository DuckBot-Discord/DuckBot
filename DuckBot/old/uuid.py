import json, random, discord, aiohttp, typing, asyncio
from random import randint
from discord.ext import commands


class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(aliases=['w', 'wh'])
    async def whitelist(self, ctx, *, argument: typing.Optional[str] = None):
        user = ctx.guild.get_member(799749818062077962)
        if argument == None:
            await ctx.message.delete()
            await ctx.send("To get whitelisted, run the `!whitelist YourMinecrftName` in the <#706842001135370300> channel. You will be automatically ")
            return
        if ctx.guild.get_role(833843541872214056) in ctx.author.roles:
            await ctx.send("⚠ Sorry but you can't do that! you're already whitelisted.")
            return
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                if cs.status == 204:
                    embed = discord.Embed(color = 0xFF2014)
                    embed.add_field(name='⚠ WHITELISTING ERROR ⚠', value=f"`{argument}` is not a minecraft username!")
                elif cs.status == 400:
                    embed = discord.Embed(color = 0xFF2014)
                    embed.add_field(name='⚠ WHITELISTING ERROR ⚠', value=f"`{argument}` is not a minecraft username!")


                elif user.status == discord.Status.online:
                    await ctx.author.add_roles(ctx.guild.get_role(833843541872214056))
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    channel = self.bot.get_channel(764631105097170974)
                    await channel.send(f'whitelist add {user}')
                    channel = self.bot.get_channel(799741426886901850)
                    embed2 = discord.Embed(title='', description=f"Automatically added user `{user}` to the whitelist", color = 0x75AF54)
                    embed2.set_footer(text=f'''{uuid}
requested by: {ctx.author.name}#{ctx.author.discriminator} | {ctx.author.id}''')
                    await channel.send(embed=embed2)
                    embed = discord.Embed(color = 0x75AF54)
                    embed.add_field(name=f'✅ YOU HAVE BEEN WHITELISTED', value=f"Your username `{user}` has been automatically whitelisted!")


                else:
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    channel = self.bot.get_channel(799741426886901850)
                    embed2 = discord.Embed(title='', description=f"{ctx.author.name}#{ctx.author.discriminator} added whitelist request for `{user}`", color = 0xF3DD53)
                    embed2.set_footer(text=f'.added {ctx.author.id}')
                    await channel.send(embed=embed2)
                    embed = discord.Embed(color = 0x75AF54)
                    embed.add_field(name=f'''✅ Whitelist request for user `{user}` added successfully!''', value=f"You will get notified once you've been whitelisted by a staff member")
                await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def added(self, ctx, member: typing.Optional[discord.Member]):
        if member == None:
            await ctx.message.add_reaction('⁉')
            await asyncio.sleep(5)
            await ctx.message.delete()
            return
        channel = self.bot.get_channel(799741426886901850)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.author.add_roles(ctx.guild.get_role(833843541872214056))
        try:
            embed = discord.Embed(color=0x00FF00)
            embed.add_field(name='OZ-smp whitelisting',value="✅ you have been manually whitelisted!")
            await member.send(embed=embed)
            embed = discord.Embed(title=f'✅ **{member.name}#{member.discriminator}** whitelisted', color=0x00FF00)
            await channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"{member}'s DMs are closed.")

def setup(bot):
    bot.add_cog(help(bot))
