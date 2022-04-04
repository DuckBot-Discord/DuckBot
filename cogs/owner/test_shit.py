from __future__ import annotations
from typing import Optional

from utils import DuckCog

from utils.command import command

async def _constrict_input(ctx):
    return ('one', 'two')

class TestingShit(DuckCog):
    
    @command(name='cock')
    async def cock(self, ctx, foo_bar: str = None, one: str = 'COCK') -> None: # type: ignore
        return await ctx.send(f'HII {one}')
    
    @cock.autocomplete('one')
    async def cock_autocomplete(self, ctx):
        return ('one', 'two')
    