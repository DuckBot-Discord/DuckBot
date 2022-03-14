from __future__ import annotations

import contextlib
import io
import sys
import time
import discord
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    TypeVar,
)

from jishaku.modules import package_version
from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.features.python import PythonFeature
from jishaku.features.root_command import RootCommand, natural_size
from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.repl import AsyncCodeExecutor, get_var_dict_from_ctx
from jishaku.paginators import use_file_check, PaginatorInterface, WrappedPaginator

from ..context import DuckContext
from .. import add_logging

try:
    import psutil
except ImportError:
    psutil = None

if TYPE_CHECKING:
    from bot import DuckBot

T = TypeVar('T')


class OverwrittenRootCommand(RootCommand):

    @Feature.Command(parent=None, name='jsk', aliases=['jishaku', 'jishacum'],
                     invoke_without_command=True)
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
            ""
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(f"Using {natural_size(mem.rss)} physical memory and "
                                       f"{natural_size(mem.vms)} virtual memory, "
                                       f"{natural_size(mem.uss)} of which unique to this process.")
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
                shard_ids = ', '.join(str(i) for i in self.bot.shards.keys())
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
            guild_subscriptions = f"guild subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}"

            summary.append(f"{message_cache} and {guild_subscriptions}.")

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms")

        summ = "\n".join(summary)
        if ctx.channel.permissions_for(ctx.me).embed_links:
            embed = discord.Embed(description=summ, color=ctx.bot.colour)
            await ctx.send(embed=embed)
        else:
            await ctx.send(summ)


features = list(STANDARD_FEATURES)
features.remove(RootCommand)
features.append(OverwrittenRootCommand)


class DuckBotJishaku(*features, *OPTIONAL_FEATURES):

    async def jsk_python_result_handling(
            self,
            ctx: DuckContext,
            result: Any,
            *,
            start_time: Optional[float] = None,
            redirect_stdout: Optional[str] = None,
    ) -> Optional[discord.Message]:
        if isinstance(result, discord.Message):
            return await ctx.send(f'<Message <{result.jump_url}>>')

        elif isinstance(result, discord.File):
            return await ctx.send(file=result)

        elif isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        elif isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        if not isinstance(result, str):
            result = repr(result)

        stripper = '**Redirected stdout**:\n{}'
        total = 2000
        if redirect_stdout:
            total -= len(f'{stripper.format(redirect_stdout)}\n')

        if len(result) <= total:
            if result.strip == '':
                result = '\u200b'

            if redirect_stdout:
                result = f'{stripper.format(redirect_stdout)}\n{result}'

            return await ctx.send(result.replace(self.bot.http.token, "[token omitted]"))

        if use_file_check(ctx, len(result)):  # File "full content" preview limit
            # Discord's desktop and web client now supports an interactive file content
            #  display for files encoded in UTF-8.
            # Since this avoids escape issues and is more intuitive than pagination for
            #  long results, it will now be prioritized over PaginatorInterface if the
            #  resultant content is below the filesize threshold
            return await ctx.send(file=discord.File(
                filename="output.py",
                fp=io.BytesIO(result.encode('utf-8'))
            ))

        # inconsistency here, results get wrapped in codeblocks when they are too large
        #  but don't if they're not. probably not that bad, but noting for later review
        paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

        if redirect_stdout:
            for chunk in self.bot.chunker(f'{stripper.format(redirect_stdout).replace("**", "")}\n', size=1975):
                paginator.add_line(chunk)

        for chunk in self.bot.chunker(result, size=1975):
            paginator.add_line(chunk)

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @discord.utils.copy_doc(PythonFeature.jsk_python)
    @Feature.Command(parent='jsk', name='py', aliases=['python'])
    async def jsk_python(self, ctx: DuckContext, *, argument: codeblock_converter) -> None:
        """|coro|
        
        The subclassed jsk python command to implement some more functionality and features.
        
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
        arg_dict['add_logging'] = add_logging
        arg_dict['self'] = self
        arg_dict['_'] = self.last_result

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
                        async for send, result in AsyncSender(executor):
                            self.last_result = result

                            value = printed.getvalue()
                            send(await self.jsk_python_result_handling(
                                ctx,
                                result,
                                start_time=start,
                                redirect_stdout=None if value == '' else value,
                            ))

        finally:
            scope.clear_intersection(arg_dict)


async def setup(bot: DuckBot) -> None:
    return await bot.add_cog(DuckBotJishaku(bot=bot))
