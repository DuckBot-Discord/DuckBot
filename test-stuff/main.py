import discord, asyncpg, asyncio, typing
from discord.ext import commands

PRE = '$'
async def get_pre(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(PRE)(bot,message)
    prefix = await bot.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', message.guild.id)
    if not prefix:
        prefix = PRE
    return commands.when_mentioned_or(prefix)(bot,message)


bot = commands.Bot(command_prefix=get_pre)

async def create_db_pool():
    description = "This is leo's test bot"

    credentials = {"user": "ubuntu", "password": "leosofia", "database": "testdb", "host": "127.0.0.1"}
    bot.db = await asyncpg.create_pool(**credentials)
    print("connection successful")

    await bot.db.execute("CREATE TABLE IF NOT EXISTS prefixes(guild_id bigint PRIMARY KEY, prefix text);")
    print("table done")

@bot.event
async def on_ready():
    print(f"Ready! logged in as {bot.user.name}")

@bot.command()
async def test(ctx):
    await ctx.send("<:maxwellsus2:863246342250692620> why")

@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def prefix(ctx, new=None):
    if not new:
        prefix = await bot.db.fetch('SELECT prefix FROM prefixes WHERE guild_id = $1', ctx.guild.id)
        prefix = prefix[0].get("prefix")
        await ctx.send(f"my prefix here is `{prefix}`")
        return

    if len(new) > 5:
        return await ctx.send("Prefixes can only be up to 5 characters")
    await bot.db.execute('UPDATE prefixes SET prefix = $1 WHERE guild_id = $2', new, ctx.guild.id)
    await ctx.send(f"prefix updated to `{new}`")



bot.loop.run_until_complete(create_db_pool())
bot.run("ODcxMjAwODIwOTkyMDQ5MTcy.YQX2_Q.24mNjTtDCkH7aI_0eVqb2eMtPGs")
