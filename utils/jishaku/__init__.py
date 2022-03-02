from __future__ import annotations

import io
import time
import contextlib
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    TypeVar,
)

import discord
import humanize

from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.features.python import PythonFeature
from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.repl import AsyncCodeExecutor, get_var_dict_from_ctx
from jishaku.paginators import use_file_check, PaginatorInterface, WrappedPaginator

from ..context import DuckContext
from .. import add_logging

if TYPE_CHECKING:
    from bot import DuckBot
    
T = TypeVar('T')


class DuckBotJishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    
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
    
    
def setup(bot: DuckBot) -> None:
    return bot.add_cog(DuckBotJishaku(bot=bot))