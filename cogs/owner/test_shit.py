from __future__ import annotations
from typing import Optional

from utils import DuckCog

from utils.command import command, group

async def _constrict_input(ctx):
    return ('one', 'two')

class TestingShit(DuckCog):
    
    @group(name='cock', invoke_without_command=True)
    async def cock(self, ctx, foo_bar: Optional[int] = None, one: str = 'COCK') -> None: # type: ignore
        if ctx.invoked_subcommand:
            return
        
        return await ctx.send(f'{foo_bar} {one}')
    
    @cock.autocomplete('foo_bar')
    async def cock_autocomplete(self, ctx, value):
        return ('one', 'two')
    
    @cock.command(name='foo')
    async def cock_foo(self, ctx):
        return await ctx.send('FOO')