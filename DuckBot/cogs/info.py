import json, random, typing, discord, asyncio, time, os, inspect, itertools
from discord.ext import commands

class about(commands.Cog):
    """😮 Bot information."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(  help="Checks the bot's ping to Discord")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
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
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def info(self, ctx):
        information = await self.bot.application_info()
        embed = discord.Embed(title='DuckBot info', color=ctx.me.color, description=f"""
**<:role:860644904048132137> Author:**
{information.owner}
**<:servers:870152102759006208> Servers:**
i'm in {len(self.bot.guilds)} servers.
<:invite:860644752281436171> Invite me [here]({self.bot.invite_url})!
**<:info:860295406349058068> Information**
[<:github:744345792172654643> source]({self.bot.repo}) | [<:topgg:870133913102721045> top.gg]({self.bot.vote_top_gg}) | [<:botsgg:870134146972938310> bots.gg]({self.bot.vote_bots_gg})
> Try also `{ctx.prefix}source [command|command.subcommand
""")

        embed.add_field(name='Bug report and support:', value= """To give a suggestion and report a bug, typo, issue or anything else DM DuckBot""", inline=False)

        await ctx.send(embed=embed)

    @commands.command(help="Links to the bot's code, or a specific command's",aliases = ['sourcecode', 'code'], usage="[command|command.subcommand]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def source(self, ctx, *, command: str = None):
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master/DuckBot'
        if command is None:
            embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my surce code]({source_url})**")
            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my surce code]({source_url})**", title="command not found")
                return await ctx.send(embed=embed)

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
        embed=discord.Embed(color=ctx.me.color,
                            description=f"**[source for `{command}`]({final_url})**")
        embed.set_footer(   text=f"{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}")
        await ctx.send(embed=embed)



    @commands.command(help="Shows duckbot's privacy policies")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def privacy(self, ctx):
        embed = discord.Embed(title=f'{ctx.me.name} Privacy Policy', description=f"""
We don't store any user data _yet_ :wink:

Privacy concerns, DM the bot.""", color=ctx.me.color)
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(about(bot))
