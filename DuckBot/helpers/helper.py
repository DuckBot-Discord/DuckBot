import discord, asyncio, json, yaml



async def success(ctx):
    await ctx.message.add_reaction("✅")
    await asyncio.sleep(3)
    try: await ctx.message.delete()
    except:return
    return

async def error(ctx, error):
    embed = discord.Embed(  color=ctx.me.color,
                            description = f"")

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=self.yaml_data['ErrorMessageTimeout'])
        await asyncio.sleep(self.yaml_data['ErrorMessageTimeout'])
        try:
            await ctx.message.delete()
            return
        except: return
