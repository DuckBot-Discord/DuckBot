from dotenv import load_dotenv
from discord.ext import commands

bot = commands.Bot(command_prefix=commands.when_mentioned_or('*****', 'tb.'), case_insensitive=True)

bot.load_extension('jishaku')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print("======[ BOT ONLINE! ]======")
    print("Logged in as " + bot.user.name)

@bot.command()
@commands.has_permissions(administrator=True)
async def delall(ctx):
    if ctx.message.author.id != 349373972103561218:
        await ctx.send('user is not bot owner (LeoCx1000#9999)')
        return
    for channel in ctx.guild.channels:  # iterating through each guild channel
        await channel.delete()
        await asyncio.sleep(1)

@bot.command()
@commands.has_permissions(administrator=True)
async def colors(ctx):
    if ctx.message.author.id != 349373972103561218:
        await ctx.send('user is not bot owner (LeoCx1000#9999)')
        return
    embed = discord.Embed(title='ColorRoles - creation process started!', description=f"this may take up to a few minutes", color=ctx.me.color)
    await ctx.send(embed=embed)
    for role in bot.get_guild(831313673351593994).roles:
        name = role.name
        color = role.colour
        perms = role.permissions
        if name == "@everyone" or name == "testbot":
            continue
        embed = discord.Embed(title='', description=f"added `{name}`", color=color)
        await ctx.send(embed=embed)
        await ctx.guild.create_role(name=name, permissions=perms, colour=color)
        await asyncio.sleep(2)

@bot.command()
@commands.has_permissions(administrator=True)
async def remcolors(ctx):
    if ctx.message.author.id != 349373972103561218:
        await ctx.send('user is not bot owner (LeoCx1000#9999)')
        return
    role_list = []
    for role in bot.get_guild(831313673351593994).roles:
        name = role.name
        color = role.colour
        perms = role.permissions
        if name == "@everyone" or name == "testbot":
            continue
        role_list.append(name)

    guildRoleList = []
    for guildRole in ctx.guild.roles:
        guildRoleName = guildRole.name
        if guildRoleName in role_list:
            guildRoleList.append(guildRoleName)

    embed = discord.Embed(title='ColorRoles - Removing the following roles:', description=f"{guildRoleList}", color=ctx.me.color)
    await ctx.send(embed=embed)
    for RemRole in ctx.guild.roles:
        rname = RemRole.name
        rcolor = RemRole.colour
        if rname in role_list:
            embed = discord.Embed(title='', description=f"removed `{rname}`", color=rcolor)
            await ctx.send(embed=embed)
            await RemRole.delete()
            await asyncio.sleep(2)

@bot.command()
async def stop(ctx):
    await ctx.send('terminating instance!')
    await ctx.bot.logout()


bot.run(TOKEN, reconnect=True)
