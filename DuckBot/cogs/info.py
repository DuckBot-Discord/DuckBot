import json, random, typing, discord, asyncio
from discord.ext import commands

class info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.bot.remove_command("help")

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        message = await ctx.send(embed=embed)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await asyncio.sleep(0.6)
        embed = discord.Embed(title='', description=f'**{round (self.bot.latency * 1000)} ms**', color=ctx.me.color)
        await message.edit(embed=embed)


    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(title='DuckBot info', description="Here's information about my bot:", color=ctx.me.color)

        # give info about you here
        embed.add_field(name='Author', value='LeoCx1000#9999', inline=True)

        # Shows the number of servers the bot is member of.
        embed.add_field(name='Server count', value="i'm in " + f'{len(self.bot.guilds)}' + " servers", inline=True)

        # give users a link to invite this bot to their server
        embed.add_field(name='Invite', value='Invite me to your server [here](https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot)', inline=True)

        embed.add_field(name='Source code', value="[Here](https://github.com/LeoCx1000/discord-bots)'s my sourcecode", inline=True)

        embed.add_field(name='Support server', value="There's no support server anymore. DM DuckBot for help", inline=True)

        embed.add_field(name='_ _', value='_ _', inline=False)

        embed.add_field(name='Bug report and support:', value= """To give a suggestion and report a bug, typo, issue or anything else DM DuckBot""", inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases = ['source', 'code'])
    async def sourcecode(self, ctx):
        embed=discord.Embed(title="", description="**[Here's my source code](https://github.com/LeoCx1000/discord-bots)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def help(self, ctx, argument: typing.Optional[str] = "None", number: typing.Optional[int] = 1):

        botprefix = '.'

        if (argument == "None"):

            embed = discord.Embed(title='DuckBot help', description=("""Hey {}, Here is a list of commands:
fields: `<obligatory>` `[optional]`""".format(ctx.message.author.mention)), color = ctx.me.color)
            embed.add_field(name='_ _', value='_ _', inline=False)
            embed.add_field(name=botprefix + 'help commands', value='Show normal commands', inline=True)
            embed.add_field(name=(botprefix + 'help testing'), value='shows testing/beta commands.', inline=True)
            embed.add_field(name=(botprefix + 'help moderation'), value='shows moderation commands.', inline=True)
            embed.add_field(name=(botprefix + 'info'), value='Gives info about the bot, and how to get support.', inline=True)
            embed.add_field(name=(botprefix + 'help [argument] [page]'), value='Gives this message or the other sub-categories.', inline=True)
            embed.add_field(name=(botprefix + 'log'), value='Gives an update log', inline=True)
            embed.add_field(name='_ _', value="""ℹ some commands are having issues. i'm currently working on debugging them. if you run a command and it doesn't work, DM the bot with the command (use `code format` because it will not send actual commands trough the modmail!)

For further help, DM the bot or join the support server found in the `.info` command""", inline=False)
            embed.set_footer(text='Bot by LeoCx1000#9999', icon_url='https://i.imgur.com/DTLCaur.gif')
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        if (argument == "commands"):

            embed = discord.Embed(title='DuckBot help', description=("Hey {}, Here is a list normal/fun commands.".format(ctx.message.author.mention)), color = ctx.me.color)
            if number == 1:

                embed.add_field(name=(botprefix + 'dog'), value='Gets a random picture of a dog', inline=False)
                embed.add_field(name=(botprefix + 'cat'), value='Gets a random picture of a cat', inline=False)
                embed.add_field(name=(botprefix + 'duck'), value='Gets a random picture of a duck', inline=False)
                embed.add_field(name=(botprefix + 'motivateme'), value='Sends an affirmation', inline=False)
                embed.add_field(name=(botprefix + 'inspireme'), value='Returns an AI generated image from Inspirobot.me', inline=False)

            if number == 2:

                embed.add_field(name=(botprefix + 'ping'), value="Shwos the bot's ping to the server", inline=False)
                embed.add_field(name=(botprefix + 'help [arg] [page]'), value='Gives a list of arguments', inline=False)
                embed.add_field(name=(botprefix + 'afk'), value='Sets/unsets you as AFK. (adds `[AFK]` to your nickname)', inline=False)
                embed.add_field(name=(botprefix + 'say <string>'), value="Makes the bot speak for you:sparkles:", inline=False)
                embed.add_field(name=(botprefix + 'uuid <player>'), value='[MINECRAFT] Gives the UUID of a given player', inline=False)

            if number == 3:

                embed.add_field(name=(botprefix + 'info'), value="Shwos info about the bot", inline=False)
                embed.add_field(name=(botprefix + 'log'), value="an update log", inline=False)
                embed.add_field(name=(botprefix + f'nick <@user> [NewNick]'), value="changes your nickname", inline=False)

            embed.add_field(name='_ _', value=f'Help commands | page `{number}/3`', inline=False)
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        if (argument == "testing"):

            embed = discord.Embed(title='DuckBot help', description=("Hey {}, Here is a list of beta/testing commands. These might not work.".format(ctx.message.author.mention)), color = ctx.me.color)
            embed.add_field(name='_ _', value='_ _', inline=False)


            embed.add_field(name='_ _', value='_ _', inline=False)
            embed.add_field(name='_ _', value=f'Help commands | page `{number}/1`', inline=False)
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        if (argument == "moderation"):

            if number == 1:
                embed = discord.Embed(title='DuckBot help', description=("Hey {}, Here is a list of beta/testing commands. These might not work.".format(ctx.message.author.mention)), color = ctx.me.color)
                embed.add_field(name='_ _', value='_ _', inline=False)
                embed.add_field(name=(botprefix + 'purge <amount>'), value='Purges messages in a channel. Limit: 1000 messages.', inline=False)
                embed.add_field(name=(botprefix + 'kick <member> [reason]'), value='kicks a member.', inline=False)
                embed.add_field(name=(botprefix + 'ban <member> [reason]'), value='bans a member.', inline=False)
                embed.add_field(name=(botprefix + 'nick <member> [NewNick]'), value="changes a member's nickname", inline=False)

            embed.add_field(name='_ _', value=f'Help commands | page `{number}/1`', inline=False)
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return

        if (argument == "owner"):
            if ctx.message.author.id == 349373972103561218:
                embed = discord.Embed(title='BOT MANAGEMENT COMMANDS', description=("Hey {}, Here are administration commands.".format(ctx.message.author.mention)), color = ctx.me.color)
                embed.add_field(name='_ _', value='_ _', inline=False)
                embed.add_field(name=(botprefix + 'load <cog>'), value='Loads a cog.', inline=False)
                embed.add_field(name=(botprefix + 'unload <cog>'), value='Unloads a cog.', inline=False)
                embed.add_field(name=(botprefix + 'reload <cog>'), value='Reloads a cog.', inline=False)
                embed.add_field(name=(botprefix + 'setstatus'), value='Sets the status of the bot.', inline=False)
                embed.add_field(name=(botprefix + 'dm'), value='Sends a DM.', inline=False)
                embed.add_field(name=(botprefix + 'shutdown'), value='Shuts down the bot.', inline=False)
                embed.add_field(name=(botprefix + 'edit <msgID> <new message> <tag>'), value="""Edits a bot't message
**tags:** `--s` removes embed. `--d` deletes content.""", inline=False)
                await ctx.send(embed=embed)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return
                return
            else:
                embed = discord.Embed(title='DuckBot error', description=("Hey {}, You are not allowed to run this command!".format(ctx.message.author.mention)), color = ctx.me.color)
                await ctx.message.delete()
                await ctx.send(embed=embed)

        if (argument != "None" and argument != "testing" and argument != "commands" and argument != "moderation" and argument != "owner"):

            embed = discord.Embed(title='DuckBot help', description='Incorrect argument. type `.help` for a list of available arguments', color = ctx.me.color)
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return
            return


    @commands.command()
    async def log(self, ctx):

        embed = discord.Embed(title='DuckBot update log', description="Latest updates of the bot:", color=ctx.me.color)

        embed.add_field(name='**`01-01-2021`**', value='Fixed issue that sent 2 un-afk messages when a message was sent', inline=False)

        embed.add_field(name='**`01-01-2021`**', value='Temporarily disabled automatic un-afk feature due to error.', inline=False)

        embed.add_field(name='**`01-01-2021`**', value='Began adding UUID command, under Testing category. Preparing to switch to async requests', inline=False)

        embed.add_field(name='**`02-01-2021`**', value=':sparkles: new support server added to help commands', inline=False)

        embed.add_field(name='**`04-01-2021`**', value='fixed support server invite', inline=False)

        embed.add_field(name='**`04-01-2021`**', value='fixed .say command to supress @everyone and @here', inline=False)

        embed.add_field(name='**`05-01-2021`**', value='UUID command passed beta testing', inline=False)

        embed.add_field(name='**`08-01-2021`**', value='edited .edit command from ID to REPLY', inline=False)

        embed.add_field(name='**`08-01-2021`**', value='added reply/quote support for .say command', inline=False)

        embed.add_field(name='**`08-01-2021`**', value='switched from requests to AioHTTP', inline=False)

        embed.add_field(name='**`11-01-2021`**', value='Fixed issue in .edit command', inline=False)

        embed.add_field(name='**`13-01-2021`**', value='Edited DM command, so it no longer needs to be executed in the same guild as the bot, allowing for responses to the DMS of the bot', inline=False)

        embed.add_field(name='**`14-01-2021`**', value='New arguments added to `.cat` command, check `.cat help` commands for more', inline=False)

        embed.add_field(name='Suggest an update/feature:', value='Just DM me (the bot) to do that ;)', inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(info(bot))
