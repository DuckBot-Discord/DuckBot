import typing, discord, asyncio, yaml
from discord.ext import commands

class promote(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_order = []
            for roleid in full_yaml['StaffOrder']:
                staff_order.append(self.bot.get_guild(717140270789033984).get_role(roleid))
            BaseStaff = self.bot.get_guild(717140270789033984).get_role(full_yaml['BaseStaff'])
        self.staff_order = staff_order
        self.BaseStaff = BaseStaff
        self.yaml_data = full_yaml

    #--------------- FUNCTIONS ---------------#

    #await self.perms_error(ctx)
    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        await asyncio.sleep(self.yaml_data['ReactionTimeout'])
        try: await ctx.message.delete()
        except: return

    #await self.error_message(ctx, 'TEXT')
    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
        await asyncio.sleep(self.yaml_data['ErrorMessageTimeout'])
        await ctx.message.delete()
        return

def setup(bot):
    bot.add_cog(promote(bot))
