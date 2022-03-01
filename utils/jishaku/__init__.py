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
        short: bool = False
    ):
        embed = discord.Embed(
            title='Python REPL Return Result' if not short else '',
            description=repr(result).replace(self.bot.http.token, "[token omitted]"),
        )
        
        if redirect_stdout and redirect_stdout != '':
            embed.add_field(name='Redirect Stdout:', value=redirect_stdout.replace(self.bot.http.token, "[token omitted]"))
        
        if not short:
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            
            if start_time:
                embed.set_footer(text=f'Took {time.perf_counter() - start_time:.2f} seconds')
        
        if isinstance(result, discord.Message):
            embed.add_field(name='Jump to message', value=f'[Jump to message]({result.jump_url})')
            return await ctx.send(embed=embed)

        if isinstance(result, discord.File):
            fmt = [
                f'**Filename**: {(filename := result.filename)}',
                f'**Size**: {len(result.fp.read())} bytes.',
                f'**Spoiler**: {result.spoiler}',
            ]
            embed.add_field(name='Metadata', value='\n'.join(fmt))
            
            # LEO THS ISNT SETTING THE IMAGE ALTHOUGH IT SHOULD BE
            # THE IF STATEMENT IS CORRECT BUT THE SET IMAGE IS NOT WORKING PLS FIX
            if filename and filename.endswith(('jpg', 'png', 'jpeg', 'gif')):
                embed.set_image(url=f'attachment://{filename}')
            
            return await ctx.send(embed=embed, file=result)

        if isinstance(result, discord.Embed):
            return await ctx.send(embeds=[embed, result])

        if isinstance(result, PaginatorInterface):
            await ctx.send(embed=embed)
            return await result.send_to(ctx)

        if not isinstance(result, str):
            # repr all non-strings
            result = repr(result)

        # Eventually the below handling should probably be put somewhere else
        if len(result) <= 2000:
            if result.strip() == '':
                embed.description = "\u200b"

            return await ctx.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none()
            )

        if use_file_check(ctx, len(result)):  # File "full content" preview limit
            # Discord's desktop and web client now supports an interactive file content
            #  display for files encoded in UTF-8.
            # Since this avoids escape issues and is more intuitive than pagination for
            #  long results, it will now be prioritized over PaginatorInterface if the
            #  resultant content is below the filesize threshold
            return await ctx.send(embed=embed, file=discord.File(
                filename="output.py",
                fp=io.BytesIO(result.encode('utf-8'))
            ))

        # inconsistency here, results get wrapped in codeblocks when they are too large
        #  but don't if they're not. probably not that bad, but noting for later review
        paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)
        paginator.add_line(result)

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
                        
                        # Thanks Jishaku  for the amazing lib that I dont need to jump through
                        # hoops to fix SO GOOD OMG ILYSM :):):):):):):):):):):):):):):)
                        #:):):):):):):):):):):):):):):):):):):):):):):):):):):):):):):):)
                        index = 0
                        async for send, result in AsyncSender(executor):
                            self.last_result = result
                            
                            send(await self.jsk_python_result_handling(
                                ctx, 
                                result, 
                                start_time=start, 
                                redirect_stdout=printed.getvalue(),
                                short=False if index == 0 else True
                            ))
                            
                            index += 1
        finally:
            scope.clear_intersection(arg_dict)
    
    
def setup(bot: DuckBot) -> None:
    return bot.add_cog(DuckBotJishaku(bot=bot))