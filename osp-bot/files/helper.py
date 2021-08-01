import discord, asyncio, json, yaml

#------------- YAML STUFF -------------#
with open(r'files/config.yaml') as file:
    full_yaml = yaml.full_load(file)
self.yaml_data = full_yaml

async def error(ctx, message):
    embed = discord.Embed(color=ctx.me.color)
    embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
    await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
    try: await ctx.message.delete(delay=self.yaml_data['ErrorMessageTimeout'])
    except: pass

async def success(ctx):
    await ctx.message.add_reaction("✅")
    await asyncio.sleep(3)
    try: await ctx.message.delete()
    except: pass
