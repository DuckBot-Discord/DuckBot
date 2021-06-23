import discord, asyncio

async def success(ctx):
    await ctx.message.add_reaction("✅")
    await asyncio.sleep(3)
    try: await ctx.message.delete()
    except:return
    return

async def failed(ctx, e, message):
    traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
    await asyncio.sleep(0.5)
    embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error\n```{traceback_string}```")
    try: await message.edit(embed=embed)
    except:
        embed = discord.Embed(color=ctx.me.color, description = f"❌ Execution error ```\n error too long, check the console\n```")
        await message.edit()
    raise e
