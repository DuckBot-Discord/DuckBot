from __future__ import annotations

import itertools
import textwrap
from typing import Optional, Any, List, Callable
from enum import Enum

import discord
import regex

from discord.ext import commands

from utils import DuckContext
from .tokens import Token, ALL_TOKENS, TokenParsingError

regex.DEFAULT_VERSION = regex.VERSION1


class SomethingWentWrong(commands.CommandError): ...


class Separator(Enum):
    OR = 0
    AND = 1


BRACES = {'{': '}', '(': ')', '[': ']', None: None}


class SearchResult:
    def __init__(self, parent: Optional[SearchResult] = None, opening_brace: Optional[str] = None) -> None:
        self._parent: Optional[SearchResult] = parent
        self.predicates: List[Token | Separator | SearchResult] = []
        self.closing_brace: Optional[str] = BRACES[opening_brace]

    @property
    def root_parent(self) -> SearchResult:
        if self._parent:
            return self._parent.root_parent
        return self

    def child(self, opening_brace: str) -> SearchResult:
        child = SearchResult(parent=self, opening_brace=opening_brace)
        self.add_pred(child)
        return child

    def parent(self):
        if self._parent:
            return self._parent
        raise SomethingWentWrong('No parent found')

    def add_pred(self, pred: Token | Separator | SearchResult):
        try:
            previous = self.predicates[-1]
            if not isinstance(pred, SearchResult) and isinstance(previous, pred.__class__):
                raise SomethingWentWrong('Somehow two of the same pred type got chained.')
            self.predicates.append(pred)
        except IndexError:
            if isinstance(pred, Separator):
                raise SomethingWentWrong('Cannot start with separator')
            self.predicates.append(pred)

    def build_predicate(self) -> Callable[[discord.Message], bool]:
        if len(self.predicates) == 1:
            predicate = self.predicates[0]
            if isinstance(predicate, Token):
                return predicate.check
            elif isinstance(predicate, SearchResult):
                return predicate.build_predicate()
            else:
                raise SomethingWentWrong('Wrong predicate found')

        built_pred: Callable[..., Any] | None = None
        previous: Callable[..., Any] | None = None
        pairwise = itertools.pairwise(self.predicates)
        for current, subsequent in pairwise:
            if isinstance(current, Token):
                previous = current.check
            elif isinstance(current, SearchResult):
                previous = current.build_predicate()
            else:
                if isinstance(subsequent, SearchResult):
                    subsequent = subsequent.build_predicate()
                elif isinstance(subsequent, Token):
                    subsequent = subsequent.check
                else:
                    raise SomethingWentWrong('Something borked.')

                print(current)

                if current is Separator.AND:
                    meth = lambda x, y: x and y
                else:
                    meth = lambda x, y: x or y

                built_pred = lambda msg: meth(previous(msg), subsequent(msg))  # type: ignore

        return built_pred  # type: ignore

    async def init(self, ctx: DuckContext):
        try:
            for pred in self.predicates:
                if isinstance(pred, Token):
                    await pred.parse(ctx)
                elif isinstance(pred, SearchResult):
                    await pred.init(ctx)
        except TokenParsingError as error:
            leading_ws = len(error.token.argument) - len(error.token.argument.lstrip())
            message = "Unrecognised search term...\n" + textwrap.indent(
                '```\n'
                + error.token.full_string
                + '\n'
                + (' ' * (error.token.start - len(error.token.invoked_with) - 1))
                + ('~' * (len(error.token.invoked_with) + 1 + leading_ws))
                + ('^' * ((error.token.stop or len(error.token.full_string)) - error.token.start - leading_ws))
                + '\n'
                + str(error.error)
                + '```',
                '> ',
            )
            raise commands.BadArgument(message)

    def all_tokens(self):
        for pred in self.predicates:
            if isinstance(pred, Token):
                yield pred
            elif isinstance(pred, SearchResult):
                yield from pred.all_tokens()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} predicates={self.predicates} closing_brace={self.closing_brace!r}>"


def next_until(n: int, idx: int, enumerator: enumerate):
    if idx >= n:
        return
    for idx, _ in enumerator:
        if idx >= n - 1:
            return


# TODO this:
"""

handle errors returned in converters

give more elaborate error messages n stuff with ^^^
"""

token_map: dict[str, type[Token]] = {}
for token in ALL_TOKENS:
    if isinstance(token.name, tuple):
        token_map.update({name.lower(): token for name in token.name})
    else:
        token_map[token.name.lower()] = token

full = '|'.join(regex.escape(k) for k in token_map.keys())

token_re = regex.compile(
    # fmt: off
    r"(?:(?P<parentheses>[\)\]\}]+)\Z|(?P<parentheses>[\)\]\}]+)?\ ?\b(?P<separator>and|or)?\ ?\b(?P<directive>" + full + r"):)",
    # This regex: It either is a parentheses at the end of the string, or it's a directive (like `from:` or `has:`) and could potentially
    # have some a separator (and|or) and before, some closing parentheses too.
    flags=regex.IGNORECASE,
    # fmt: on
)


class PurgeSearchConverter:
    async def convert(self, ctx: DuckContext, unparsed: str) -> SearchResult:
        scanner = token_re.finditer(unparsed)

        current = SearchResult()
        match = next(scanner)
        start, end = match.span(0)
        enumerator = enumerate(unparsed)
        for idx, char in enumerator:
            if char in BRACES:
                current = current.child(char)

            elif idx == start:
                closing_braces: Optional[str] = match.group('parentheses')
                if closing_braces:
                    for brace in closing_braces:
                        if brace != current.closing_brace:
                            raise SomethingWentWrong(f'Unmatched parentheses. {brace} - {current.closing_brace}')

                        current = current.parent()

                directive: str = match.group('directive')
                separator: Optional[str] = match.group('separator')

                if current.predicates and directive and not separator:
                    separator = 'and'

                if separator:
                    current.add_pred(Separator.AND if separator.lower() == 'and' else Separator.OR)
                    next_until(end, idx, enumerator)

                try:
                    next_match = next(scanner)
                    next_start, next_end = next_match.span(0)

                    if directive:
                        token_cls = token_map[directive]
                        token = token_cls(unparsed, end, next_start, invoked_with=directive, result_found_at=current)

                        current.add_pred(token)
                    else:
                        next_until(len(unparsed), idx, enumerator)
                        continue

                    match, start, end = next_match, next_start, next_end

                    next_until(next_start, idx, enumerator)
                except StopIteration:
                    if directive:
                        token_cls = token_map[directive]
                        token = token_cls(unparsed, end, None, invoked_with=directive, result_found_at=current)

                        current.add_pred(token)
                        next_until(len(unparsed), idx, enumerator)

        if current.closing_brace:
            raise SomethingWentWrong('Unclosed parentheses.')

        return current.root_parent
