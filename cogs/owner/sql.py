from __future__ import annotations
import io

import time
from tabulate import tabulate
from typing import List, Annotated

from import_expression import eval
from discord import File
from discord.ext.commands import FlagConverter, flag, Converter
from utils import DuckCog, DuckContext, command, UntilFlag

from .eval import cleanup_code


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, _, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'


class EvaluatedArg(Converter):
    async def convert(self, ctx: DuckContext, argument: str) -> str:
        return eval(cleanup_code(argument), {'bot': ctx.bot, 'ctx': ctx})


class SqlCommandFlags(FlagConverter, prefix="--", delimiter=" ", case_insensitive=True):
    args: List[str] = flag(name='argument', aliases=['a', 'arg'], converter=List[EvaluatedArg], default=[])


class SQLCommands(DuckCog):
    @command()
    async def sql(self, ctx: DuckContext, *, query: UntilFlag[Annotated[str, cleanup_code], SqlCommandFlags]):
        """|coro|

        Executes an SQL query

        Parameters
        ----------
        query: str
            The query to execute.
        """
        is_multistatement = query.value.count(';') > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = ctx.bot.pool.execute
        else:
            strategy = ctx.bot.pool.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query.value, *query.flags.args)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception as e:
            return await ctx.send(f'{type(e).__name__}: {e}')

        rows = len(results)
        if rows == 0 or isinstance(results, str):
            result = 'Query returned 0 rows' if rows == 0 else str(results)
            await ctx.send(f'`{result}`\n*Ran in {dt:.2f}ms*')

        else:
            table = tabulate(results, headers='keys', tablefmt='orgtbl')

            fmt = f'```\n{table}\n```*Returned {plural(rows):row} in {dt:.2f}ms*'
            if len(fmt) > 2000:
                fp = io.BytesIO(table.encode('utf-8'))
                await ctx.send(
                    f'*Too many results...\nReturned {plural(rows):row} in {dt:.2f}ms*', file=File(fp, 'output.txt')
                )
            else:
                await ctx.send(fmt)
