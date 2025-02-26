from __future__ import annotations

import contextlib
import io
import pprint
import random
import re

import aiohttp
import textwrap
import traceback
import typing
import datetime

import asyncio
import discord
from discord.ext import commands
from import_expression import exec as e_exec

from utils import DuckCog, DuckContext, DeleteButton, command, UntilFlag, FlagConverter, cb
from bot import DuckBot

CODEBLOCK_REGEX = re.compile(r'`{3}(python\n|py\n|\n)?(?P<code>[^`]*)\n?`{3}')


class EvalFlags(FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    wrap: bool = commands.flag(aliases=['executor', 'exec'], default=False)


def cleanup_code(content: str):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    content = textwrap.dedent(content).strip()
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class react(contextlib.AbstractAsyncContextManager):
    def __init__(self, message: discord.Message) -> None:
        self.message = message
        self.bot: DuckBot = message._state._get_client()  # type: ignore
        self.task: typing.Optional[asyncio.Task] = None
        self.exc: typing.Optional[BaseException] = None

    async def starting_reaction(self) -> None:
        await asyncio.sleep(1.5)
        try:
            await self.message.add_reaction('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}')
        except discord.HTTPException:
            pass

    async def ending_reaction(self, exception: typing.Optional[BaseException]):
        if not exception:
            await self.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        elif isinstance(exception, asyncio.TimeoutError):
            await self.message.add_reaction('\N{STOPWATCH}')
        else:
            await self.message.add_reaction('\N{WARNING SIGN}')

    async def __aenter__(self):
        self.task = self.bot.create_task(self.starting_reaction())
        return self

    async def __aexit__(self, *args) -> bool:
        if self.task:
            self.task.cancel()
        self.bot.create_task(self.ending_reaction(self.exc))
        return False


class Eval(DuckCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_result = None
        self._last_context_menu_input = None

    @staticmethod
    def handle_return(ret: typing.Any, stdout: str | None = None) -> dict | None:
        kwargs = {}
        if isinstance(ret, discord.File):
            kwargs['files'] = [ret]
        elif isinstance(ret, discord.Message):
            kwargs['content'] = f"{repr(ret)}"
        elif isinstance(ret, Exception):
            kwargs['content'] = "".join(traceback.format_exception(type(ret), ret, ret.__traceback__))
        elif ret is None:
            pass
        else:
            kwargs['content'] = f"{ret}"

        if stdout:
            kwargs['content'] = f"{kwargs.get('content', '')}{stdout}"

        if (content := kwargs.pop('content', None)) and len(content) > 1990:
            files = kwargs.get('files', [])
            file = discord.File(io.BytesIO(content.encode()), filename='output.py')
            files.append(file)
            kwargs['files'] = files
        elif content:
            kwargs['content'] = cb(content)

        return kwargs or None

    def clean_globals(self):
        return {
            '__name__': __name__,
            '__package__': __package__,
            '__file__': __file__,
            '__builtins__': __builtins__,
            'annotations': annotations,
            'traceback': traceback,
            'io': io,
            'typing': typing,
            'asyncio': asyncio,
            'discord': discord,
            'commands': commands,
            'datetime': datetime,
            'aiohttp': aiohttp,
            're': re,
            'random': random,
            'pprint': pprint,
            '_get': discord.utils.get,
            '_find': discord.utils.find,
            '_now': discord.utils.utcnow,
            'bot': self.bot,
            '_': self._last_result,
        }

    async def eval(
        self, body: str, env: typing.Dict[str, typing.Any], wrap: bool = False, reactor: typing.Optional[react] = None
    ) -> dict | None:
        """Evaluates arbitrary python code"""
        env.update(self.clean_globals())

        stdout = io.StringIO()

        if wrap:
            to_compile = f'def func():\n{textwrap.indent(body, "  ")}'
        else:
            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            e_exec(to_compile, env)
        except Exception as e:
            if reactor:
                reactor.exc = e
            return self.handle_return(e)

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                if wrap:
                    ret = await self.bot.wrap(func)
                else:
                    ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            if reactor:
                reactor.exc = e
            return self.handle_return(e, stdout=value)

        else:
            value = stdout.getvalue()
            if ret is not None:
                self._last_result = ret
            return self.handle_return(ret, stdout=value)

    @command(name='eval')
    async def eval_command(self, ctx: DuckContext, *, body: UntilFlag[typing.Annotated[str, cleanup_code], EvalFlags]):
        """Evaluates arbitrary python code"""
        env = {
            'ctx': ctx,
            'channel': ctx.channel,
            '_c': ctx.channel,
            'author': ctx.author,
            '_a': ctx.author,
            'guild': ctx.guild,
            '_g': ctx.guild,
            'message': ctx.message,
            '_m': ctx.message,
            '_r': getattr(ctx.message.reference, 'resolved', None),
        }

        result = None
        async with react(ctx.message) as reactor:
            result = await self.eval(body.value, env, wrap=body.flags.wrap, reactor=reactor)

        if result:
            await DeleteButton.send_to(**result, destination=ctx, author=ctx.author)
