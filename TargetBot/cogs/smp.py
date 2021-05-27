import typing, discord, asyncio, yaml, aiohttp
from discord.ext import commands

class moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            self.staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                self.staff_roles.append(self.bot.get_guild(717140270789033984).get_role(roleid))
        self.console = self.bot.get_channel(full_yaml['ConsoleCommandsChannel'])
        self.yaml_data = full_yaml
        self.modrole = self.bot.get_guild(717140270789033984).get_role(full_yaml['SMPModeratorRole'])

    #--------------- FUNCTIONS ---------------#

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(self.yaml_data['ReactionTimeout'])
        try: await ctx.message.delete()
        except: return

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
        await asyncio.sleep(self.yaml_data['ErrorMessageTimeout'])
        await ctx.message.delete()
        return

    async def namecheck(self, argument):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                if cs.status == 204: user = None
                elif cs.status == 400: user = None
                else:
                    res = await cs.json()
                    user = res["name"]
                return user

#---------------------------------------------------------------#
#------------------------ GameBan ------------------------------#
#---------------------------------------------------------------#

    @commands.command(aliases=['smpban', 'gban'])
    async def GameBan(self, ctx, argument: typing.Optional[str] = 'invalid name', *, reason = None):
        if not self.modrole in ctx.author.roles:
            await self.perms_error(ctx)
            return
        name = await self.namecheck(argument)
        if name:
            if reason:
                await self.console.send(f'ban {name} {reason}')
                embed=discord.Embed(description=f"""{ctx.author.mention} banned **{name}** from the server
```reason: {reason}```""", color=ctx.me.color)
            else:
                await self.console.send(f'ban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} banned **{name}** from the server""", color=ctx.me.color)
            await ctx.send(embed=embed)
        else:
            await self.error_message(ctx, 'That username is invalid!')

#-----------------------------------------------------------------#
#------------------------ GameUnban ------------------------------#
#-----------------------------------------------------------------#

    @commands.command(aliases=['smpunban', 'gunban'])
    async def GameUnban(self, ctx, argument: typing.Optional[str] = 'invalid name', *, reason = None):
        if not self.modrole in ctx.author.roles:
            await self.perms_error(ctx)
            return
        name = await self.namecheck(argument)
        if name:
            if reason:
                await self.console.send(f'unban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} unbanned **{name}** from the server
```reason: {reason}```""", color=ctx.me.color)
            else:
                await self.console.send(f'unban {name}')
                embed=discord.Embed(description=f"""{ctx.author.mention} unbanned **{name}** from the server""", color=ctx.me.color)
            await ctx.send(embed=embed)
        else:
            await self.error_message(ctx, 'That username is invalid!')





def setup(bot):
    bot.add_cog(moderation(bot))
