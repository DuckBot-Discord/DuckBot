from __future__ import annotations

import contextlib
import io
import itertools
import sys
import time
import traceback
from typing import TYPE_CHECKING, Annotated, Any, Optional, TypeVar

import discord
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.features.management import ManagementFeature
from jishaku.features.python import PythonFeature
from jishaku.features.root_command import RootCommand
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.math import natural_size
from jishaku.modules import ExtensionConverter, package_version
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor
from jishaku.repl.repl_builtins import get_var_dict_from_ctx

from utils.bases.context import DuckContext

from .. import DuckCog, add_logging

try:
    import psutil
except ImportError:
    psutil = None

if TYPE_CHECKING:
    from bot import DuckBot

T = TypeVar("T")


class OverwrittenRootCommand(RootCommand):
    @Feature.Command(
        parent=None,
        name="jsk",
        aliases=["jishaku", "jishacum"],
        invoke_without_command=True,
    )
    async def jsk(self, ctx: DuckContext):
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """

        summary = [
            f"Jishaku v{package_version('jishaku')}, discord.py `{package_version('discord.py')}`, "
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"Module was loaded <t:{self.load_time.timestamp():.0f}:R>, "
            f"cog was loaded <t:{self.start_time.timestamp():.0f}:R>.",
            "",
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(
                            f"Using {natural_size(mem.rss)} physical memory and "
                            f"{natural_size(mem.vms)} virtual memory, "
                            f"{natural_size(mem.uss)} of which unique to this process."
                        )
                    except psutil.AccessDenied:
                        pass

                    try:
                        name = proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()

                        summary.append(f"Running on PID {pid} (`{name}`) with {thread_count} thread(s).")
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line

        cache_summary = f"{len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s)"

        # Show shard settings to summary
        if isinstance(self.bot, discord.AutoShardedClient):
            if len(self.bot.shards) > 20:
                summary.append(
                    f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                    f" and can see {cache_summary}."
                )
            else:
                shard_ids = ", ".join(str(i) for i in self.bot.shards.keys())
                summary.append(
                    f"This bot is automatically sharded (Shards {shard_ids} of {self.bot.shard_count})"
                    f" and can see {cache_summary}."
                )
        elif self.bot.shard_count:
            summary.append(
                f"This bot is manually sharded (Shard {self.bot.shard_id} of {self.bot.shard_count})"
                f" and can see {cache_summary}."
            )
        else:
            summary.append(f"This bot is not sharded and can see {cache_summary}.")

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:
            message_cache = f"Message cache capped at {self.bot._connection.max_messages}"
        else:
            message_cache = "Message cache is disabled"

        if discord.version_info >= (1, 5, 0):
            presence_intent = f"presence intent is {'enabled' if self.bot.intents.presences else 'disabled'}"
            members_intent = f"members intent is {'enabled' if self.bot.intents.members else 'disabled'}"

            summary.append(f"{message_cache}, {presence_intent} and {members_intent}.")
        else:
            guild_subscriptions = f"guild subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}"  # type: ignore

            summary.append(f"{message_cache} and {guild_subscriptions}.")

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms")

        summ = "\n".join(summary)
        if ctx.channel.permissions_for(ctx.me).embed_links:  # type: ignore
            embed = discord.Embed(description=summ, color=ctx.bot.colour)
            await ctx.send(embed=embed)
        else:
            await ctx.send(summ)


class OverwrittenManagementFeature(ManagementFeature):
    @Feature.Command(parent="jsk", name="load", aliases=["reload"])
    async def jsk_load(self, ctx: DuckContext, *extensions: ExtensionConverter):
        """
        Loads or reloads the given extension names.

        Reports any extensions that failed to load.
        """
        paginator = WrappedPaginator(prefix="", suffix="")

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == "reload" and not extensions:
            extensions = [["utils.jishaku"]]  # type: ignore

        for extension in itertools.chain(*extensions):  # type: ignore
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await discord.utils.maybe_coroutine(method, extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True,
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)


features = list(STANDARD_FEATURES)
features.remove(RootCommand)
features.append(OverwrittenRootCommand)
features.remove(ManagementFeature)
features.append(OverwrittenManagementFeature)


class DuckBotJishaku(
    DuckCog,
    *features,
    *OPTIONAL_FEATURES,
):
    """
    The main frontend class for JIshaku.

    This implements all Features and is the main entry point for Jishaku.

    Attributes
    ----------
    bot: :class:`DuckBot`
        The bot instance this frontend is attached to.
    """

    __is_jishaku__: bool = True

    async def jsk_python_result_handling(
        self,
        ctx: DuckContext,
        result: Any,
        *,
        start_time: Optional[float] = None,
        redirect_stdout: Optional[str] = None,
    ):
        if isinstance(result, discord.Message):
            return await ctx.send(f"<Message <{result.jump_url}>>")

        elif isinstance(result, discord.File):
            return await ctx.send(file=result)

        elif isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        elif isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        if not isinstance(result, str):
            result = repr(result)

        stripper = "**Redirected stdout**:\n{}"
        total = 2000
        if redirect_stdout:
            total -= len(f"{stripper.format(redirect_stdout)}\n")

        if len(result) <= total:
            if result.strip == "":
                result = "\u200b"

            if redirect_stdout:
                result = f"{stripper.format(redirect_stdout)}\n{result}"

            return await ctx.send(result.replace(self.bot.http.token or "", "[token omitted]"))

        if use_file_check(ctx, len(result)):  # File "full content" preview limit
            # Discord's desktop and web client now supports an interactive file content
            #  display for files encoded in UTF-8.
            # Since this avoids escape issues and is more intuitive than pagination for
            #  long results, it will now be prioritized over PaginatorInterface if the
            #  resultant content is below the filesize threshold
            return await ctx.send(file=discord.File(filename="output.py", fp=io.BytesIO(result.encode("utf-8"))))

        # inconsistency here, results get wrapped in codeblocks when they are too large
        #  but don't if they're not. probably not that bad, but noting for later review
        paginator = WrappedPaginator(prefix="```py", suffix="```", max_size=1985)

        if redirect_stdout:
            for chunk in self.bot.chunker(f'{stripper.format(redirect_stdout).replace("**", "")}\n', size=1975):
                paginator.add_line(chunk)

        for chunk in self.bot.chunker(result, size=1975):
            paginator.add_line(chunk)

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @discord.utils.copy_doc(PythonFeature.jsk_python)
    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx: DuckContext, *, argument: Annotated[Codeblock, codeblock_converter]) -> None:
        """The subclassed jsk python command to implement some more functionality and features.

        Added
        -----
        - :meth:`contextlib.redirect_stdout` to allow for print statements.
        - :meth:`utils.add_logging` and `self` to the scope.

        Parameters
        ----------
        argument: :class:`str`
            The code block to evaluate and return.
        """

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict.update(
            add_logging=add_logging,
            self=self,
            _=self.last_result,
            _r=getattr(ctx.message.reference, 'resolved', None),
            _a=ctx.author,
            _m=ctx.message,
            _now=discord.utils.utcnow,
            _g=ctx.guild,
        )

        scope = self.scope
        printed = io.StringIO()

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    with contextlib.redirect_stdout(printed):
                        executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                        start = time.perf_counter()

                        # Absolutely a garbage lib that I have to fix jesus christ.
                        # I have to rewrite this lib holy jesus its so bad.
                        async for send, result in AsyncSender(executor):  # type: ignore
                            self.last_result = result

                            value = printed.getvalue()
                            send(
                                await self.jsk_python_result_handling(
                                    ctx,
                                    result,
                                    start_time=start,
                                    redirect_stdout=None if value == "" else value,
                                )
                            )

        finally:
            scope.clear_intersection(arg_dict)


async def setup(bot: DuckBot) -> None:
    return await bot.add_cog(DuckBotJishaku(bot=bot))
