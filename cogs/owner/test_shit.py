from __future__ import annotations

import typing
from typing import List
from collections import Counter
from typing import NamedTuple

import discord
from discord.ext import commands
from discord.ext.commands.view import StringView

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


def int_reactions(number: int) -> List[str]:
    """
    Returns a list of strings that represent the reactions.

    Parameters
    ----------
    number: int
        The number of reactions to return.

    Returns
    -------
    List[str]
        A list of strings that represent the reactions.
    """
    if not isinstance(number, int):
        raise TypeError("number must be an int")

    characters = list(str(number))
    if any(i > 2 for i in Counter(characters).values()):
        return ["\N{PERMANENT PAPER SIGN}"]  # :infinity:
    added = set()
    for char in characters:
        if char in added:
            yield f"{char}\N{VARIATION SELECTOR-16}\N{combining enclosing keycap}"
        else:
            added.add(char)
            yield f"{char}\N{combining enclosing keycap}"


class TestingShit(DuckCog):
    @commands.command()
    async def test(self, ctx: DuckContext, *, args: CatConverter):
        await ctx.send(
            "\n-----------------\n".join(
                f"role = {a.role.mention} ({type(a.role).__name__})"  # type: ignore
                f"\ndescription = {a.description} ({type(a.description).__name__})"  # type: ignore
                f"\nemoji = {str(a.emoji)} ({type(a.emoji).__name__})"  # type: ignore
                for a in args
            )
        )

    @commands.command()
    async def test2(
        self,
        ctx: DuckContext,
        *,
        arg: discord.Member = commands.param(converter=discord.Member, default=commands.Author, displayed_default="user"),
    ):
        await ctx.send(str(arg))
