import asyncio
import contextlib
import datetime
import importlib
import inspect
import io
import itertools
import math
import os
import random
import re
import textwrap
import traceback
import typing
from collections import defaultdict

import discord
import emoji as unicode_emoji
import import_expression
import jishaku.modules
import tabulate
from discord.ext import commands
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.features.baseclass import Feature
from jishaku.paginators import WrappedPaginator
from jishaku.shim.paginator_200 import PaginatorInterface

from bot import DuckBot, CustomContext
from helpers import paginator, constants

RebootArg = typing.Optional[typing.Union[bool, typing.Literal["reboot", "restart", "r"]]]


class EvalJobCancelView(discord.ui.View):
    def __init__(
        self,
        bot: DuckBot,
        *,
        cog: commands.Cog,
        user_message: discord.Message,
        ctx: CustomContext,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx
        self.cog: Management = cog  # type: ignore
        self.user_message = user_message

    @discord.ui.button(label="repeat", emoji="🔁")
    async def re_run(self, inter: discord.Interaction, _):
        await self.cog._eval_edit(self.ctx, self.user_message.content, inter.message)  # type: ignore

    @discord.ui.button(emoji="🗑", label="End session")
    async def end_session(self, inter: discord.Interaction, _):
        await inter.message.delete()  # type: ignore
        self.stop()

    async def interaction_check(self, interaction) -> bool:
        return interaction.user and (await self.bot.is_owner(interaction.user))


# SQL table formatter by "SYCK UWU" over on the duckbot discord
def format_table(db_res):
    result_dict = defaultdict(list)
    for x in db_res:
        for k, value in x.items():
            result_dict[k].append(value)

    def key(i):
        return len(i)

    # I just wrote some weird code and it worked lmfao
    total_length = [
        (len(max([str(column_name)] + [str(row) for row in rows], key=key)) + 2) for column_name, rows in result_dict.items()
    ]
    result = "┍" + ("┯".join("━" * times for times in total_length)) + "┑" + "\n│"
    columns = [str(col) for col in result_dict.keys()]
    rows = [list() for _, _1 in enumerate(list(result_dict.values())[0])]
    for row in result_dict.values():
        for index, item in enumerate(row):
            rows[index].append(item)

    column_lengths = list()
    for index, column in enumerate(columns):
        column_length = len(max([str(column)] + [str(row[index]) for row in rows], key=key)) + 2
        column_lengths.append(column_length)
        before = math.ceil((column_length - len(column)) / 2)
        after = math.floor((column_length - len(column)) / 2)
        result += (" " * before) + column + (" " * after) + "│"
    result += "\n" + "┝" + ("┿".join("━" * times for times in total_length)) + "┥\n│"

    for row in rows:
        for index, item in enumerate(row):
            before = math.ceil((column_lengths[index] - len(str(item))) / 2)
            after = math.floor((column_lengths[index] - len(str(item))) / 2)
            result += (" " * before) + str(item) + (" " * after) + "│"
        result += "\n" + "┝" + ("┿".join("━" * times for times in total_length)) + "┥\n│"

    result = "\n".join(result.split("\n")[:-2])
    result += "\n" + "┕" + ("┷".join("━" * times for times in total_length)) + "┙"

    return result


async def setup(bot):
    await bot.add_cog(Management(bot))


async def get_webhook(channel) -> discord.Webhook:
    if isinstance(channel, discord.Thread):
        channel = channel.parent
    webhook_list = await channel.webhooks()
    if webhook_list:
        for hook in webhook_list:
            if hook.token:
                return hook
    hook = await channel.create_webhook(name="DuckBot Webhook", avatar=await channel.guild.me.display_avatar.read())
    return hook


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:-1])

    # remove `foo`
    return content.strip("` \n")


def is_reply():
    def predicate(ctx):
        if not ctx.message.reference:
            raise commands.BadArgument("You must reply to a message!")
        return True

    return commands.check(predicate)


class UnicodeEmoji:
    @classmethod
    async def convert(cls, ctx, argument):
        if argument not in list(unicode_emoji.EMOJI_UNICODE_ENGLISH.values()):
            return None
        return argument


def get_syntax_error(e):
    if e.text is None:
        return f"```py\n{e.__class__.__name__}: {e}\n```"
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'


class Management(commands.Cog, name="Bot Management"):
    """
    🤖 Commands meant for the bot developers to manage the bots functionalities. Not meant for general use.
    """

    def __init__(self, bot):
        self.sessions = set()
        self.bot: DuckBot = bot
        self._last_result = None

    # Git but to the correct directory
    @Feature.Command(parent="jsk", name="git")
    async def jsk_git(self, ctx: CustomContext, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh git'. Invokes the system shell.
        """
        return await ctx.invoke(
            "jsk shell",
            argument=Codeblock(argument.language, "cd ~/.git/DiscordBots\ngit " + argument.content),
        )

    @commands.command(help="Unloads an extension", aliases=["unl", "ue", "uc"])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def unload(self, ctx, extension):
        embed = discord.Embed(color=ctx.me.color, description=f"⬇ {extension}")
        message = await ctx.send(embed=embed, footer=False)
        try:
            self.bot.unload_extension("cogs.{}".format(extension))
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"✅ {extension}")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not found")
            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            await asyncio.sleep(0.5)
            embed = discord.Embed(color=ctx.me.color, description=f"❌ Extension not loaded")
            await message.edit(embed=embed)

    @commands.command(help="Reloads all extensions", aliases=["relall", "rall", "reloadall", "load"])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reload(self, ctx, *extensions: jishaku.modules.ExtensionConverter):
        self.bot.last_rall = datetime.datetime.utcnow()
        pages = WrappedPaginator(prefix="", suffix="")
        to_send = []
        err = False
        first_reload_failed_extensions = []

        extensions = extensions or [await jishaku.modules.ExtensionConverter().convert(ctx, "~")]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )
            # noinspection PyBroadException
            try:
                await method(extension)
                pages.add_line(f"{icon} `{extension}`")
            except Exception:
                first_reload_failed_extensions.append(extension)

        error_keys = {
            commands.ExtensionNotFound: "Not found",
            commands.NoEntryPointError: "No setup function",
            commands.ExtensionNotLoaded: "Not loaded",
            commands.ExtensionAlreadyLoaded: "Already loaded",
        }

        for extension in first_reload_failed_extensions:
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )
            try:
                await method(extension)
                pages.add_line(f"{icon} `{extension}`")

            except tuple(error_keys.keys()) as exc:
                pages.add_line(f"{icon}❌ `{extension}` - {error_keys[type(exc)]}")

            except commands.ExtensionFailed as e:
                traceback_string = f"```py" f"\n{''.join(traceback.format_exception(e))}" f"\n```"
                pages.add_line(f"{icon}❌ `{extension}` - Execution error")
                to_dm = f"❌ {extension} - Execution error - Traceback:"

                if (len(to_dm) + len(traceback_string) + 5) > 2000:
                    await ctx.author.send(file=io.StringIO(traceback_string))
                else:
                    await ctx.author.send(f"{to_dm}\n{traceback_string}")

        for page in pages.pages:
            await ctx.send(page)

    @commands.command(name="mreload", aliases=["mload", "mrl", "rlm"])
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def reload_module(self, ctx, *modules: jishaku.modules.ExtensionConverter):
        """
        Reloads one or multiple extensions
        """
        pages = WrappedPaginator(prefix="", suffix="")

        if not modules:
            extensions = [await jishaku.modules.ExtensionConverter().convert(ctx, "helpers.*")]
        else:
            extensions: list[list[str]] = modules  # type: ignore

        for extension in itertools.chain(*extensions):
            icon = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"

            try:
                module = importlib.import_module(extension)
                importlib.reload(module)

            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                pages.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True,
                )
            else:
                pages.add_line(f"{icon} `{extension}`")

        pages.add_line('Remember to reload extensions that use this module!')
        for page in pages.pages:
            await ctx.send(page)

    ###############################################################################
    ###############################################################################

    @commands.command(pass_context=True, hidden=True, name="eval", aliases=["ev"])
    @commands.is_owner()
    async def _eval(self, ctx: CustomContext, *, body: str, return_result: bool = False):
        """Evaluates arbitrary python code"""
        env = {
            "bot": self.bot,
            "_b": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "_c": ctx.channel,
            "author": ctx.author,
            "_a": ctx.author,
            "guild": ctx.guild,
            "_g": ctx.guild,
            "message": ctx.message,
            "_m": ctx.message,
            "_": self._last_result,
            "reference": getattr(ctx.message.reference, "resolved", None),
            "_r": getattr(ctx.message.reference, "resolved", None),
            "_get": discord.utils.get,
            "_find": discord.utils.find,
            "_gist": ctx.gist,
            "_now": discord.utils.utcnow,
        }
        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        to_send: str = None

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            import_expression.exec(to_compile, env)
        except Exception as e:
            try:
                await ctx.message.add_reaction("⚠")
            except (discord.Forbidden, discord.HTTPException):
                pass
            to_send = f"{e.__class__.__name__}: {e}"
            if len(to_send) > 1880:
                return await ctx.send(file=discord.File(io.StringIO(to_send), filename="output.py"))
            await ctx.send(f"```py\n{to_send}\n```")
            return

        func = env["func"]
        # noinspection PyBroadException
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("⚠")
            except (discord.Forbidden, discord.HTTPException):
                pass
            to_send = f"\n{value}{traceback.format_exc()}"
            if len(to_send) > 1880:
                await ctx.send(file=discord.File(io.StringIO(to_send), filename="output.py"))
                return
            await ctx.send(f"```py\n{to_send}\n```")
            return

        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except (discord.Forbidden, discord.HTTPException):
                pass

            if not return_result:
                if ret is None:
                    if value:
                        to_send = f"{value}"
                else:
                    self._last_result = ret
                    to_send = f"{value}{ret}"
                if to_send:
                    to_send = to_send.replace(self.bot.http.token, "[discord token redacted]")
                    if len(to_send) > 1985:
                        await ctx.send(file=discord.File(io.StringIO(to_send), filename="output.py"))
                    else:
                        await ctx.send(f"```py\n{to_send}\n```")
            else:
                return ret

    @commands.command(pass_context=True, hidden=True)
    async def repl(self, ctx, *, flags: None = None):
        """Launches an interactive REPL session."""
        variables = {
            "bot": self.bot,
            "_b": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "_c": ctx.channel,
            "author": ctx.author,
            "_a": ctx.author,
            "guild": ctx.guild,
            "_g": ctx.guild,
            "message": ctx.message,
            "_m": ctx.message,
            "_": None,
            "reference": getattr(ctx.message.reference, "resolved", None),
            "_r": getattr(ctx.message.reference, "resolved", None),
            "_get": discord.utils.get,
            "_find": discord.utils.find,
            "_gist": ctx.gist,
            "_now": discord.utils.utcnow,
        }

        if ctx.channel.id in self.sessions:
            await ctx.send("Already running a REPL session in this channel. Exit it with `quit`.")
            return

        self.sessions.add(ctx.channel.id)
        await ctx.send("Enter code to execute or evaluate. `exit()` or `quit` to exit.")

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.startswith("`")

        while True:
            try:
                response = await self.bot.wait_for("message", check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await ctx.send("Exiting REPL session.")
                self.sessions.remove(ctx.channel.id)
                break

            cleaned = cleanup_code(response.content)

            if cleaned in ("quit", "exit", "exit()"):
                await ctx.send("Exiting.")
                self.sessions.remove(ctx.channel.id)
                return

            executor = exec
            if cleaned.count("\n") == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, "<repl session>", "eval")
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, "<repl session>", "exec")
                except SyntaxError as e:
                    await ctx.send(get_syntax_error(e))
                    continue

            variables["message"] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with contextlib.redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = f"```py\n{value}{traceback.format_exc()}\n```"
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = f"```py\n{value}{result}\n```"
                    variables["_"] = result
                elif value:
                    fmt = f"```py\n{value}\n```"

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await ctx.send("Content too big to be printed.")
                    else:
                        await ctx.send(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send(f"Unexpected error: `{e}`")

    # Dev commands. `if True` is only to be able to close or "fold" the whole category at once
    if True:

        @commands.group()
        @commands.is_owner()
        async def dev(self, ctx: commands.Context):
            """Base command for dev commands"""
            return

        @dev.command(name="ban", aliases=["blacklist", "ba", "block"])
        async def dev_ban(self, ctx: CustomContext, user: discord.User, *, reason: str = None):
            """Bot-bans a user"""

            await self.bot.db.execute(
                "INSERT INTO blacklist(user_id, is_blacklisted, reason) VALUES ($1, $2, $3) "
                "ON CONFLICT (user_id) DO UPDATE SET is_blacklisted = $2, reason = $3",
                user.id,
                True,
                reason,
            )

            self.bot.blacklist[user.id] = True

            await ctx.send(f"Added **{user}** to the blacklist")

        @dev.command(name="unban", aliases=["un-blacklist", "br", "unblock"])
        async def dev_unban(self, ctx: CustomContext, user: discord.User) -> discord.Message:
            """Bot-unbans a user"""

            await self.bot.db.execute("DELETE FROM blacklist where user_id = $1", user.id)

            self.bot.blacklist.pop(user.id, None)

            await ctx.send(f"Removed **{user}** from the blacklist")

        @dev.command(name="ban-check", aliases=["bc", "blacklist-check", "blc"])
        async def dev_ban_check(self, ctx: CustomContext, user: discord.User):
            """Checks a user's blacklist status"""
            if user.id in self.bot.blacklist:
                if reason := await self.bot.db.fetchval("SELECT reason FROM blacklist WHERE user_id = $1", user.id):
                    return await ctx.send(f"**{user}** is blacklisted for {reason}")
                return await ctx.send(f"**{user}** is blacklisted without a reason")
            await ctx.send(f"**{user}** is not blacklisted")

        @dev.command(
            name="bans",
            aliases=["bl", "bl-list", "blocked", "banlist", "blacklist-list"],
        )
        async def dev_blacklist_list(self, ctx: CustomContext):
            """Lists all users on the blacklist"""
            blacklist = await self.bot.db.fetch("SELECT user_id, reason FROM blacklist")
            if not blacklist:
                return await ctx.send("No users are blacklisted")
            table = [(self.bot.get_user(user_id), user_id, reason or "No reason given") for user_id, reason in blacklist]
            table = tabulate.tabulate(table, headers=["User", "User ID", "Reason"], tablefmt="presto")
            lines = table.split("\n")
            lines, headers = lines[2:], "\n".join(lines[0:2])
            header = f"DuckBot blacklist".center(len(lines[0]))
            pages = jishaku.paginators.WrappedPaginator(prefix=f"```\n{header}\n{headers}", max_size=1950)
            [pages.add_line(line) for line in lines]
            interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
            await interface.send_to(ctx)

        @dev.command(name="user-history", aliases=["uh", "mh", "member-history", "ucmds"])
        async def dev_user_history(self, ctx: CustomContext, user: discord.User):
            """Lists all users on the blacklist"""
            executed_commands = await self.bot.db.fetch(
                "SELECT command, guild_id, timestamp FROM commands WHERE user_id = $1 " "ORDER BY timestamp DESC",
                user.id,
            )
            if not executed_commands:
                return await ctx.send("No results found...")
            table = [
                (
                    command,
                    guild_id or "ran in DMs",
                    str(timestamp).replace("+00:00", ""),
                )
                for command, guild_id, timestamp in executed_commands
            ]
            table = tabulate.tabulate(table, headers=["Command", "Guild ID", "Timestamp"], tablefmt="presto")
            lines = table.split("\n")
            lines, headers = lines[2:], "\n".join(lines[0:2])
            header = f"Commands by {user}".center(len(lines[0]))
            pages = jishaku.paginators.WrappedPaginator(prefix=f"```\n{header}\n{headers}", max_size=1950)
            [pages.add_line(line) for line in lines]
            interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
            await interface.send_to(ctx)

        @dev.command(
            name="guild-history",
            aliases=["gh", "sh", "server-history", "scmds", "gcmds"],
        )
        async def dev_server_history(self, ctx: CustomContext, guild: discord.Guild):
            """Lists all users on the blacklist"""
            executed_commands = await self.bot.db.fetch(
                "SELECT command, user_id, timestamp FROM commands WHERE guild_id = $1 " "ORDER BY timestamp DESC",
                guild.id,
            )
            if not executed_commands:
                return await ctx.send("No results found...")
            table = [
                (
                    command,
                    self.bot.get_user(user_id) or user_id,
                    str(timestamp).replace("+00:00", ""),
                )
                for command, user_id, timestamp in executed_commands
            ]
            table = tabulate.tabulate(table, headers=["Command", "User/UID", "Timestamp"], tablefmt="presto")
            lines = table.split("\n")
            lines, headers = lines[2:], "\n".join(lines[0:2])
            header = f"Latest commands in {guild}".center(len(lines[0]))
            pages = jishaku.paginators.WrappedPaginator(prefix=f"```\n{header}\n{headers}", max_size=1950)
            [pages.add_line(line) for line in lines]
            interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
            await interface.send_to(ctx)

        @dev.group(name="command-history", aliases=["ch", "cmds"], invoke_without_command=True)
        async def dev_all_history(
            self,
            ctx: CustomContext,
            arg: typing.Optional[typing.Union[discord.User, discord.Guild]] = None,
        ):
            """Lists all users on the blacklist"""
            if arg:
                if isinstance(arg, discord.User):
                    return await self.dev_user_history(ctx, arg)
                elif isinstance(arg, discord.Guild):
                    return await self.dev_server_history(ctx, arg)
            executed_commands = await self.bot.db.fetch(
                "SELECT command, user_id, guild_id, timestamp FROM commands ORDER BY timestamp DESC"
            )
            if not executed_commands:
                return await ctx.send("No results found...")
            table = [
                (
                    command,
                    self.bot.get_user(user_id) or user_id,
                    guild_id,
                    str(timestamp).replace("+00:00", ""),
                )
                for command, user_id, guild_id, timestamp in executed_commands
            ]
            table = tabulate.tabulate(
                table,
                headers=["Command", "User/UID", "Guild ID", "Timestamp"],
                tablefmt="presto",
            )
            lines = table.split("\n")
            lines, headers = lines[2:], "\n".join(lines[0:2])
            header = f"Latest executed commands".center(len(lines[0]))
            pages = jishaku.paginators.WrappedPaginator(prefix=f"```\n{header}\n{headers}", max_size=1950)
            [pages.add_line(line) for line in lines]
            interface = jishaku.paginators.PaginatorInterface(self.bot, pages)
            await interface.send_to(ctx)

        @dev_all_history.command(name="clear")
        async def dev_all_history_clear(self, ctx: CustomContext):
            """Clears all command history"""
            await self.bot.db.execute("DELETE FROM commands")
            await ctx.message.add_reaction("✅")

        @dev.group(
            name="sql",
            aliases=["db", "database", "psql", "postgre"],
            invoke_without_command=True,
        )
        @commands.is_owner()
        async def dev_sql(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database"""
            body = cleanup_code(query)
            await ctx.invoke(self._eval, body=f'return await bot.db.execute(f"""{body}""")')

        @dev_sql.command(name="pretty-fetch", aliases=["pfetch", "pf"])
        async def postgre_fetch_pretty(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database (Fetch | Prettyfied)"""
            body = cleanup_code(query)
            result = await self._eval(
                ctx,
                body=f'return await bot.db.fetch(f"""{body}""")',
                return_result=True,
            )
            if not result:
                return await ctx.send("No results found...")
            else:
                result = format_table(result)
                await ctx.send(f"```py\n{result}\n```", maybe_attachment=True, extension="txt")

        @dev_sql.command(name="fetch", aliases=["f"])
        async def postgre_fetch(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database (Fetch)"""
            body = cleanup_code(query)
            await ctx.invoke(self._eval, body=f'return await bot.db.fetchval(f"""{body}""")')

        @dev_sql.command(name="fetchval", aliases=["fr"])
        async def postgre_fetchval(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database (Fetchval)"""
            body = cleanup_code(query)
            await ctx.invoke(self._eval, body=f'return await bot.db.fetchval(f"""{body}""")')

        @dev_sql.command(name="fetchrow", aliases=["fv"])
        async def postgre_fetchrow(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database (Fetchrow)"""
            body = cleanup_code(query)
            await ctx.invoke(self._eval, body=f'return await bot.db.fetchrow(f"""{body}""")')

        @dev_sql.command(name="execute", aliases=["e"])
        async def postgre_execute(self, ctx: CustomContext, *, query: str):
            """Executes an SQL query to the database (Execute)"""
            body = cleanup_code(query)
            await ctx.invoke(self._eval, body=f'return await bot.db.execute(f"""{body}""")')

        @is_reply()
        @dev.command()
        async def react(self, ctx, emoji: typing.Optional[typing.Union[UnicodeEmoji, discord.Emoji]]):
            if emoji:
                await ctx.message.reference.resolved.add_reaction(emoji)
            await ctx.message.delete(delay=0)

        @dev.command(name="server-list", aliases=["guilds-list", "bot-servers", "guilds"])
        async def g_list(self, ctx: CustomContext):
            """
            Shows the bots servers info.
            """
            source = paginator.ServerInfoPageSource(guilds=self.bot.guilds, ctx=ctx)
            menu = paginator.ViewPaginator(source=source, ctx=ctx)
            await menu.start()

        @dev.command(aliases=["pull"], name="update")
        async def dev_git_pull(self, ctx: CustomContext, reload_everything: RebootArg = True):
            """
            Attempts to pull from git
            """
            command = self.bot.get_command("jsk git")
            await ctx.invoke(command, argument=codeblock_converter("pull"))
            if reload_everything is True:
                mrl = self.bot.get_command("mrl")
                await ctx.invoke(mrl)
                rall = self.bot.get_command("rall")
                await ctx.invoke(rall)
            elif isinstance(reload_everything, str):
                self.bot.dispatch("restart_request", ctx, "duckbot", False)

        @dev.command(aliases=["push"], name="git-push")
        async def dev_git_push(self, ctx, *, message: str):
            """Attempts to push to git"""
            command = self.bot.get_command("jsk git")
            await ctx.invoke(
                command,
                argument=codeblock_converter(f'add .\ngit commit -m "{message}"\ngit push origin master'),
            )

        @dev.command(name="eval", aliases=["e", "ev"])
        async def dev_eval(self, ctx: CustomContext, *, body: str):
            """Evaluates arbitrary python code"""
            await ctx.invoke(self._eval, body=body)

        @dev.command(aliases=["mm"], name="maintenance-mode")
        async def maintenance_mode(self, ctx, *, reason: str = None):
            if reason:
                await ctx.message.add_reaction(ctx.toggle(True))
                self.bot.maintenance = reason
            elif self.bot.maintenance:
                await ctx.message.add_reaction(ctx.toggle(False))
                self.bot.maintenance = None
            else:
                await ctx.send(f"Please provide a reason!")

        @dev.command(name="restart", aliases=["reboot", "r"])
        async def restart(self, ctx, service: str = "duckbot", daemon: bool = False):
            self.bot.dispatch("restart_request", ctx, service, daemon)

        @dev.command(aliases=["sp"], name="silent-prefix")
        @commands.bot_has_permissions(add_reactions=True)
        async def silent_prefix(self, ctx, state: bool = None):
            """ """
            if state is not None:
                await ctx.message.add_reaction(ctx.toggle(state))
                self.bot.noprefix = state
            else:
                await ctx.message.add_reaction(ctx.toggle(not self.bot.noprefix))
                self.bot.noprefix = not self.bot.noprefix

        @dev.group(aliases=["setstatus", "ss", "activity"], usage="<type> <status>")
        async def status(self, ctx: CustomContext):
            """Base command for setting the bot's status"""
            if not ctx.invoked_subcommand:
                await ctx.send_help(ctx.command)

        @status.command(name="playing")
        async def status_playing(self, ctx: CustomContext, *, text):
            """Sets the bot's status to playing"""
            await self.bot.change_presence(activity=discord.Game(name=f"{text}"))
            await ctx.message.add_reaction("✅")
            await ctx.send(f"Activity changed to `Playing {text}` ")

        @status.command(name="listening")
        async def status_listening(self, ctx: CustomContext, text):
            """Sets the bot's status to listening"""
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{text}"))
            await ctx.message.add_reaction("✅")
            await ctx.send(f"Activity changed to `Listening to {text}` ")

        @status.command(name="watching")
        async def status_watching(self, ctx: CustomContext, *, text):
            """Sets the bot's status to watching"""
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{text}"))
            await ctx.message.add_reaction("✅")
            await ctx.send(f"Activity changed to `Watching {text}` ")

        @status.command(name="competing")
        async def status_competing(self, ctx: CustomContext, *, text):
            """Sets the bot's status to competing"""
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=f"{text}"))
            await ctx.message.add_reaction("✅")
            await ctx.send(f"Activity changed to `Competing in {text}`")

        @dev.command(name="dm", aliases=["pm", "message", "direct"])
        @commands.guild_only()
        async def dev_dm(self, ctx: CustomContext, member: discord.User, *, message=None):
            if ctx.channel.category_id == 878123261525901342:
                return
            category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
            channel = discord.utils.get(category.channels, topic=str(member.id))
            if not channel:
                channel = await category.create_text_channel(
                    name=f"{member}",
                    topic=str(member.id),
                    position=0,
                    reason="DuckBot ModMail",
                )

            wh = await get_webhook(channel)

            files = []
            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if attachment.size > 8388600:
                        await ctx.send("Sent message without attachment! File size greater than 8 MB.")
                        continue
                    files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

            try:
                await member.send(content=message, files=files)
            except discord:
                return await ctx.message.add_reaction("⚠")

            try:
                await wh.send(
                    content=message,
                    username=ctx.author.name,
                    avatar_url=ctx.author.display_avatar.url,
                    files=files,
                )
            except discord.HTTPException:
                await ctx.message.add_reaction("🤖")
                await ctx.message.add_reaction("‼")
            await ctx.message.add_reaction("💌")

        @dev.command(name="acknowledge", aliases=["ack"])
        async def dev_acknowledge(self, ctx: CustomContext, user: discord.User, *, message=None):
            """Acknowledges a member"""
            if message:
                await self.bot.db.execute(
                    "INSERT INTO ack (user_id, description) VALUES ($1, $2) "
                    "ON CONFLICT (user_id) DO UPDATE SET description = $2",
                    user.id,
                    message,
                )
            else:
                await self.bot.db.execute("DELETE FROM ack WHERE user_id = $1", user.id)
            try:
                await ctx.message.add_reaction(random.choice(constants.DONE))
            except discord.HTTPException:
                pass

        @commands.max_concurrency(1, commands.BucketType.channel)
        @dev.command(name="code-space", aliases=["codespace", "cs", "python", "py", "i"])
        async def dev_cs(self, ctx: CustomContext):
            """Starts a code-space session for this channel"""
            message: discord.Message = await self.bot.wait_for(
                "message", check=lambda m: m.author == ctx.author, timeout=None
            )
            if message.content == "cancel":
                return await message.add_reaction("✖")
            bot_message = await message.reply(
                "```py\ngenerating output...\n```",
                view=EvalJobCancelView(self.bot, cog=self, user_message=message, ctx=ctx),
            )
            await self._eval_edit(ctx, message.content, bot_message)
            bot = self.bot
            while True:
                done, pending = await asyncio.wait(
                    [
                        bot.loop.create_task(
                            bot.wait_for(
                                "message",
                                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                                timeout=None,
                            )
                        ),
                        bot.loop.create_task(
                            bot.wait_for(
                                "message_edit",
                                check=lambda b, a: b.author == ctx.author and a.channel == ctx.channel,
                                timeout=None,
                            )
                        ),
                        bot.loop.create_task(
                            bot.wait_for(
                                "raw_message_delete",
                                check=lambda p: p.message_id == bot_message.id,
                                timeout=None,
                            )
                        ),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                try:
                    stuff = done.pop().result()
                    if isinstance(stuff, discord.Message):
                        try:
                            if stuff.content == "cancel":
                                await message.add_reaction("✅")
                                await bot_message.edit(view=None)
                                await stuff.add_reaction("✅")
                                return
                            else:
                                await stuff.add_reaction("📤")
                        except Exception as e:
                            await stuff.reply(f"{e}")
                    elif isinstance(stuff, discord.RawMessageDeleteEvent):
                        return await message.add_reaction("✅")
                    else:
                        _, after = stuff
                        if after.content == "cancel":
                            await bot_message.add_reaction("✅")
                            return
                        await self._eval_edit(ctx, after.content, bot_message)
                except Exception as e:
                    return await ctx.send(f"{e}")
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()

        async def _eval_edit(self, ctx: CustomContext, body, to_edit: discord.Message):
            """Evaluates code and edits the message"""
            env = {
                "bot": self.bot,
                "_b": self.bot,
                "ctx": ctx,
                "channel": ctx.channel,
                "_c": ctx.channel,
                "author": ctx.author,
                "_a": ctx.author,
                "guild": ctx.guild,
                "_g": ctx.guild,
                "message": ctx.message,
                "_m": ctx.message,
                "_": self._last_result,
                "reference": getattr(ctx.message.reference, "resolved", None),
                "_r": getattr(ctx.message.reference, "resolved", None),
                "_get": discord.utils.get,
                "_find": discord.utils.find,
                "_gist": ctx.gist,
                "_now": discord.utils.utcnow,
            }
            env.update(globals())

            body = cleanup_code(body)
            stdout = io.StringIO()

            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

            try:
                import_expression.exec(to_compile, env)
            except Exception as e:
                to_send = f"{e.__class__.__name__}: {e}"
                if len(to_send) > 1985:
                    gist = await self.bot.create_gist(filename="output.py", description="Eval output", content=to_send)
                    await ctx.typing()
                    return await to_edit.edit(content=f"**Output too long:**\n<{gist}>")
                await to_edit.edit(content=f"```py\n{to_send}\n```")
                return

            func = env["func"]
            # noinspection PyBroadException
            try:
                with contextlib.redirect_stdout(stdout):
                    ret = await func()
            except Exception:
                value = stdout.getvalue()
                to_send = f"\n{value}{traceback.format_exc()}"
                if len(to_send) > 1985:
                    gist = await self.bot.create_gist(
                        filename="output.py",
                        description="Eval output",
                        content=to_send,
                        public=False,
                    )
                    await to_edit.edit(content=f"**Output too long:**\n<{gist}>")
                    return
                await to_edit.edit(content=f"```py\n{to_send}\n```")
                return

            else:
                value = stdout.getvalue()
                if ret is None:
                    if value:
                        to_send = f"{value}"
                    else:
                        to_send = "No output."
                else:
                    self._last_result = ret
                    to_send = f"{value}{ret}"
                if to_send:
                    to_send = to_send.replace(self.bot.http.token, "[discord token redacted]")
                    if len(to_send) > 1985:
                        gist = await self.bot.create_gist(
                            filename="output.py",
                            description="Eval output",
                            content=to_send,
                            public=False,
                        )
                        await to_edit.edit(content=f"**Output too long:**\n<{gist}>")
                    else:
                        await to_edit.edit(content=f"```py\n{to_send}\n```")

        async def parse_tags(self, text: str):
            """Parses tags in a string"""
            to_r = []
            tags = await self.bot.loop.run_in_executor(
                None,
                re.findall,
                r"^\| +(?P<id>[0-9]+) +\|(?P<name>.{102})\| +(?P<user_id>[0-9]{15,19}) +\| +[0-9]+ +\| +(?P<can_delete>True|False)+ +\| +(?P<is_alias>True|False)+ +\|$",
                text,
                re.MULTILINE,
            )
            for tag_id, name, user_id, can_delete, is_alias in tags:
                to_r.append(
                    (
                        int(tag_id),
                        name.strip(),
                        int(user_id),
                        can_delete == "True",
                        is_alias == "True",
                    )
                )
            return to_r

        @dev.command(name="unclaimed")
        async def dev_unclaimed(self, ctx: CustomContext):
            """
            Parses all unclaimed tags from an attachment file.
            """

            if not ctx.reference or not ctx.reference.attachments:
                raise commands.BadArgument("No attachment found.")

            unclaimed = []
            text = (await ctx.reference.attachments[0].read()).decode("utf-8")
            parsed_tags = await self.parse_tags(text)
            for tag_id, name, user_id, _, is_alias in parsed_tags:
                print(user_id)
                if not ctx.guild.get_member(user_id):
                    unclaimed.append((name, str(self.bot.get_user(user_id) or user_id), str(is_alias), str(tag_id)))
            if not unclaimed:
                raise commands.BadArgument(f"No unclaimed tags found. searched {len(parsed_tags)} tags.")
            pages = WrappedPaginator()

            longest_user_name = max([x[1] for x in unclaimed])
            longest_tag_id = max([x[3] for x in unclaimed])

            for tag_name, user_name, is_alias, tag_id in unclaimed:
                pages.add_line(
                    f" {str(user_name).ljust(longest_user_name)} | {is_alias:<5} | {tag_id.ljust(longest_tag_id)} | {tag_name}"
                )
            interface = PaginatorInterface(self.bot, pages)
            await interface.send_to(ctx.author)
            await ctx.send(f"Delivering {len(unclaimed)} unclaimed tags to {ctx.author}'s DMs.")
