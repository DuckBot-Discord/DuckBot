from __future__ import annotations

import traceback
import typing
from contextlib import redirect_stdout
from io import StringIO
from textwrap import indent
from timeit import default_timer
from typing import NamedTuple

import discord
from discord.ext import commands
from discord.ext.commands.view import StringView

from cogs.owner.eval import cleanup_code
from utils import DuckCog, DuckContext


class Arg(NamedTuple):
    role: discord.Role | None = None
    description: str | None = None
    emoji: discord.PartialEmoji | None = None


if typing.TYPE_CHECKING:
    # typechecker happy wit dis >:)
    CatConverter = typing.List[Arg]
else:
    # runtime converter:

    async def to_str(ctx: DuckContext, string: str) -> str:
        return string

    class CatConverter(commands.Converter):
        # noinspection PyProtocol
        async def convert(self, ctx: DuckContext, argument: str):
            view = StringView(argument)
            current = 0
            args = []
            arg = Arg()
            while not view.eof:
                word = view.get_quoted_word()

                try:
                    role = await commands.RoleConverter().convert(ctx, word)
                    if arg.role:
                        args.append(arg)
                        arg = Arg(role=role)
                        view.skip_ws()
                        continue
                    arg = Arg(role=role)
                    view.skip_ws()
                except commands.RoleNotFound:
                    if arg.role:
                        try:
                            emoji = await commands.PartialEmojiConverter().convert(ctx, word)
                            new_a = Arg(emoji=emoji, role=arg.role, description=arg.description)
                            args.append(new_a)
                            arg = Arg()
                            view.skip_ws()
                            continue
                        except commands.PartialEmojiConversionFailure:
                            if not arg.description:
                                arg = Arg(description=word, role=arg.role)
                                view.skip_ws()
                            else:
                                raise
                    else:
                        raise
            return args

class TestingShit(DuckCog):
    @commands.command()
    async def test(self, ctx: DuckContext, *, args: CatConverter):
        await ctx.send('\n-----------------\n'.join(
            f"role = {a.role.mention} ({type(a.role).__name__})"
            f"\ndescription = {a.description} ({type(a.description).__name__})"
            f"\nemoji = {str(a.emoji)} ({type(a.emoji).__name__})"
            for a in args))
