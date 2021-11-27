import io
import logging
import re
import traceback

import asyncpg
import discord
import jishaku.paginators
from discord.ext import commands
from discord.ext.commands import BucketType

from ozbot import helpers


class handler(commands.Cog):
    """🆘 Handle them errors 👀"""
    def __init__(self, bot):
        self.bot = bot
        self.error_channel = 880181130408636456

    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx: commands.Context, error):
        error = getattr(error, "original", error)
        ignored = (
            commands.CommandNotFound,
            commands.DisabledCommand
        )
        if isinstance(error, ignored):
            return
        if isinstance(error, ignored):
            return

        if isinstance(error, discord.ext.commands.CheckAnyFailure):
            for e in error.errors:
                if not isinstance(error, commands.NotOwner):
                    error = e
                    break

        if isinstance(error, discord.ext.commands.BadUnionArgument):
            if error.errors:
                error = error.errors[0]

        embed = discord.Embed(color=0xD7342A)
        embed.set_author(name='Missing permissions!',
                         icon_url='https://i.imgur.com/OAmzSGF.png')

        if isinstance(error, commands.NotOwner):
            return await ctx.send(f"you must own `{ctx.me.display_name}` to use `{ctx.command}`")

        if isinstance(error, commands.TooManyArguments):
            return await ctx.send(f"Too many arguments passed to the command!")

        if isinstance(error, discord.ext.commands.MissingPermissions):
            text = f"You're missing the following permissions: \n**{', '.join(error.missing_permissions)}**"
            embed.description = text
            try:
                return await ctx.send(embed=embed)
            except discord.Forbidden:
                try:
                    return await ctx.send(text)
                except discord.Forbidden:
                    pass
                finally:
                    return

        if isinstance(error, discord.ext.commands.BotMissingPermissions):
            text = f"I'm missing the following permissions: \n**{', '.join(error.missing_permissions)}**"
            try:
                embed.description = text
                await ctx.send(embed=embed)
            except discord.Forbidden:
                await ctx.send(text)
            finally:
                return

        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            missing = f"{str(error.param).split(':')[0]}"
            command = f"{ctx.clean_prefix}{ctx.command} {ctx.command.signature}"
            separator = (' ' * (len(command.split(missing)[0]) - 1))
            indicator = ('^' * (len(missing) + 2))

            logging.info(f"`{separator}`  `{indicator}`")
            logging.info(error.param)

            return await ctx.send(f"```{command}\n{separator}{indicator}\n{missing} is a required argument that is missing.\n```")

        elif isinstance(error, commands.errors.PartialEmojiConversionFailure):
            return await ctx.send(f"`{error.argument}` is not a valid Custom Emoji")

        elif isinstance(error, commands.errors.CommandOnCooldown):
            embed = discord.Embed(color=0xD7342A,
                                  description=f'Please try again in {round(error.retry_after, 2)} seconds')
            embed.set_author(name='Command is on cooldown!',
                             icon_url='https://i.imgur.com/izRBtg9.png')

            if error.type == BucketType.default:
                per = ""
            elif error.type == BucketType.user:
                per = "per user"
            elif error.type == BucketType.guild:
                per = "per server"
            elif error.type == BucketType.channel:
                per = "per channel"
            elif error.type == BucketType.member:
                per = "per member"
            elif error.type == BucketType.category:
                per = "per category"
            elif error.type == BucketType.role:
                per = "per role"
            else:
                per = ""

            embed.set_footer(
                text=f"cooldown: {error.cooldown.rate} per {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, discord.ext.commands.errors.MaxConcurrencyReached):
            embed = discord.Embed(color=0xD7342A, description=f"Please try again once you are done running the command")
            embed.set_author(name='Command is alrady running!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.per == BucketType.default:
                per = ""
            elif error.per == BucketType.user:
                per = "per user"
            elif error.per == BucketType.guild:
                per = "per server"
            elif error.per == BucketType.channel:
                per = "per channel"
            elif error.per == BucketType.member:
                per = "per member"
            elif error.per == BucketType.category:
                per = "per category"
            elif error.per == BucketType.role:
                per = "per role"
            else:
                per = ""

            embed.set_footer(text=f"limit is {error.number} command(s) running {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.MemberNotFound):
            return await ctx.send(f"I couldn't find `{error.argument}` in this server")

        elif isinstance(error, commands.errors.UserNotFound):
            return await ctx.send(
                f"I've searched far and wide, but `{error.argument}` doesn't seem to be a member discord user...")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(error or "Bad argument given!")

        elif isinstance(error, helpers.NotOz):
            return await ctx.send('Commands are restricted to OZ!')

        error_channel = self.bot.get_channel(self.error_channel)

        traceback_string = "".join(traceback.format_exception(
            etype=None, value=error, tb=error.__traceback__))

        await self.bot.wait_until_ready()

        if ctx.me.guild_permissions.administrator:
            admin = '✅'
        else:
            admin = '❌'

        if ctx.guild:
            command_data = f"command: {ctx.message.content[0:1700]}" \
                           f"\nguild_id: {ctx.guild.id}" \
                           f"\nowner_id: {ctx.guild.owner.id}" \
                           f"\nbot admin: {admin} " \
                           f"- role pos: {ctx.me.top_role.position}"
        else:
            command_data = f"command: {ctx.message.content[0:1700]}" \
                           f"\nCommand executed in DMs"

        to_send = f"```yaml\n{command_data}``````py\n{ctx.command} " \
                  f"command raised an error:\n{traceback_string}\n```"
        if len(to_send) < 2000:
            try:
                sent_error = await error_channel.send(to_send)

            except (discord.Forbidden, discord.HTTPException):
                sent_error = await error_channel.send(f"```yaml\n{command_data}``````py Command: {ctx.command}"
                                                      f"Raised the following error:\n```",
                                                      file=discord.File(io.StringIO(traceback_string),
                                                                        filename='traceback.py'))
        else:
            sent_error = await error_channel.send(f"```yaml\n{command_data}``````py Command: {ctx.command}"
                                                  f"Raised the following error:\n```",
                                                  file=discord.File(io.StringIO(traceback_string),
                                                                    filename='traceback.py'))
        try:
            await sent_error.add_reaction('🗑')
        except (discord.HTTPException, discord.Forbidden):
            pass
        raise error


    @commands.Cog.listener('on_message')
    async def fetch_close_by(self, message: discord.Message):
        if message.author.id != 864969115839758356 or message.channel.id != 851314198654484521:
            return
        if not (match := re.search(r'FETCH_NEARBY \| (?P<X>-?\d+) \| (?P<z>-?\d+) \| (?P<Name>\w+) \| (?P<radius>-?\d+)', message.content)):
            return
        x, z, name, radius = match.group('X'), match.group('z'), match.group('Name'), match.group('radius')
        results = await self.bot.db.fetch("""
        SELECT x, z, description FROM coords 
        WHERE x 
            BETWEEN $1::INTEGER - $3::INTEGER 
            AND $1::INTEGER + $3::INTEGER 
        AND z 
            BETWEEN $2::INTEGER - $3::INTEGER 
            AND $2::INTEGER + $3::INTEGER
            """, int(x), int(z), int(radius))
        if not results:
            return await message.channel.send("""!xc tellraw insert_player_here ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"No results founds within a insert_radius_here block radius!","color":"red"}]
            """.replace('insert_radius_here', radius).replace('insert_player_here', name))
        lines = ["""{"text":"\\nxcoord","color":"yellow"},{"text":"X","color":"gold"},{"text":" zcoord","color":"yellow"},{"text":"Z","color":"gold"},{"text":" - description","color":"gray"}""".replace('xcoord', str(x)).replace('zcoord', str(z)).replace('description', description) for x, z, description in results]
        header = f"------ Locations within {radius} blocks ------"
        pages = jishaku.paginators.WrappedPaginator(prefix="", suffix="", max_size=1600)
        [pages.add_line(line) for line in lines]
        page = str(pages.pages[0]).replace('\n', ',')
        page = """!xc tellraw insert_player_here ["",{"text":"header_here","color":"blue"}table_thing{"text":"\\n---------------------------------amountstr","color":"blue"}]
        """.replace('header_here', header).replace('insert_player_here', name).replace('table_thing', page).replace('amountstr', str('-'*len(str(radius))))
        if len(page) <= 2000:
            await message.channel.send(page)
        else:
            return await message.channel.send("""!xc tellraw insert_player_here ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"The amount of characters exceeded the amount of characters allowed! Please contact Leo and tell him to fix it.","color":"red"}]
            """.replace('insert_radius_here', radius).replace('insert_player_here', name))

    @commands.Cog.listener('on_message')
    async def insert_into_database(self, message: discord.Message):
        if message.author.id != 864969115839758356 or message.channel.id != 851314198654484521:
            return
        if not (match := re.search(r"^(?P<X>-?[0-9]*) \| (?P<Z>-?[0-9]*) \| (?P<Name>\w+) \| (?P<UUID>[0-9a-f]{8}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{12}) \| (?P<Description>.*)$", message.content)):
            return
        x, z, name, uuid, description = match.group('X'), match.group('Z'), match.group('Name'), match.group('UUID'), match.group('Description')
        author_id = await self.bot.db.fetchval("SELECT user_id FROM usernames WHERE minecraft_id = $1", uuid)
        if not author_id:
            await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Succesfully saved to discord database as ","color":"gold"},{"text":"insert_discord_username ","color":"yellow"},{"text":"with annotation ","color":"gold"},{"text":"insert_note_here","color":"yellow"}]
            """.replace("insert_minecraft_username", name))
            return
        try:
            await self.bot.db.execute("INSERT INTO coords (author, x, z, description) VALUES ($1, $2, $3, $4)", author_id, int(x), int(z), description)
            await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Succesfully saved to discord database as ","color":"gold"},{"text":"insert_discord_username ","color":"yellow"},{"text":"with annotation ","color":"gold"},{"text":"insert_note_here","color":"yellow"}]
            """.replace("insert_minecraft_username", name).replace("insert_discord_username", str(self.bot.get_user(author_id) or f'User not found (ID: {author_id})')).replace("insert_note_here", description))
        except asyncpg.UniqueViolationError:
            coords_author_id = await self.bot.db.fetchval("SELECT author FROM coords WHERE x = $1 AND z = $2", int(x), int(z))
            if coords_author_id:
                await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Sorry but ","color":"red"},{"text":"insert_discord_username ","color":"yellow"},{"text":"has already saved these coordinates. ","color":"red"},{"text":"Maybe move a bit?","color":"yellow"}]
                """.replace("insert_discord_username", str(self.bot.get_user(coords_author_id) or f'User not found (ID: {coords_author_id})')).replace("insert_minecraft_username", name))
            else:
                await message.channel.send("""!xc tellraw insert_minecraft_username ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"]","bold":true,"color":"blue"},{"text":" Sorry but ","color":"red"},{"text":"insert_discord_username ","color":"yellow"},{"text":"has already saved these coordinates. ","color":"red"},{"text":"Maybe move a bit?","color":"yellow"}]
                """.replace("insert_discord_username", 'UNKNOWN USER').replace("insert_minecraft_username", name))

def setup(bot):
    bot.add_cog(handler(bot))
