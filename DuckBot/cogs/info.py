import json, random, typing, discord, asyncio, time
from discord.ext import commands

class about(commands.Cog):
    """Some information about me."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(  help="Checks the bot's ping to Discord")
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        start = time.perf_counter()
        message = await ctx.send(embed=embed)
        end = time.perf_counter()
        await asyncio.sleep(0.7)
        duration = (end - start) * 1000
        embed = discord.Embed(title='', description=f'**websocket:** `{(self.bot.latency * 1000):.2f}ms` \n**message:** `{duration:.2f}ms`', color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command(help="Shows info about the bot")
    async def info(self, ctx):
        embed = discord.Embed(title='DuckBot info', description="Here's information about my bot:", color=ctx.me.color)

        # give info about you here
        embed.add_field(name='Author', value='LeoCx1000#9999', inline=True)

        # Shows the number of servers the bot is member of.
        embed.add_field(name='Server count', value="i'm in " + f'{len(self.bot.guilds)}' + " servers", inline=True)

        # give users a link to invite this bot to their server
        embed.add_field(name='Invite', value='Invite me to your server [here](https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot)', inline=True)

        embed.add_field(name='Source code', value="[Here](https://github.com/LeoCx1000/discord-bots)'s my sourcecode", inline=True)

        embed.add_field(name='_ _', value='_ _', inline=False)

        embed.add_field(name='Bug report and support:', value= """To give a suggestion and report a bug, typo, issue or anything else DM DuckBot""", inline=False)

        await ctx.send(embed=embed)

    @commands.command(help="Links to the bot's code, or a specific command's",aliases = ['sourcecode', 'code'], usage="[command|command.subcommand]")
    @commands.command()
    async def source(self, ctx, *, command: str = None):
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master/DuckBot'
        if command is None:
            return await ctx.send(source_url)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.send('Could not find command.')

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = 'https://github.com/Rapptz/discord.py'
            branch = 'master'

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        embed=discord.embed(color=ctx.me.color, description=f"**[Here's my surce code]({final_url})")
        await ctx.send(final_url)

    @commands.command(help="Shows duckbot's privacy policies")
    async def privacy(self, ctx):
        embed = discord.Embed(title=f'{ctx.me.name} Privacy Policy', description=f"""
We don't store any user data _yet_ :wink:

Privacy concerns, DM the bot.""", color=ctx.me.color)
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(about(bot))
