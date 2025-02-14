from __future__ import annotations

import datetime
import inspect
from typing import Optional, Any, Literal, Union, List, Type, TYPE_CHECKING

import discord
import regex

from discord.ext import commands

from utils import DuckContext

if TYPE_CHECKING:
    from .parser import SearchResult

regex.DEFAULT_VERSION = regex.VERSION1

URL_REGEX = regex.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
EMOJI_REGEX = regex.compile(r'<a?:\w+:\d+>')


class TokenParsingError(Exception):
    def __init__(self, token: Token, error: Exception) -> None:
        self.token = token
        self.error = error
        super().__init__(f"Failed to parse token: `{token.invoked_with}:` because:\n{error}")


class Token:
    """Base class for purge tokens.

    Subclasses must overwrite `converter` attribute or `parse` method, and `name` attribute.
    """

    converter: Optional[Any] = NotImplemented  # The converter to be used by discord.py to parse this string later
    name: str | tuple[str, ...] = NotImplemented  # the thing that will be used to parse the text.
    #                                        # I.e. ``from`` for looking for ``from: @user``

    def __init__(self, full_string: str, start: int, stop: int | None, invoked_with: str, result_found_at: SearchResult):
        self.full_string = full_string
        self.argument = full_string[start:stop]
        self.start = start
        self.stop = stop
        self.invoked_with = invoked_with
        self.parsed_argument: Any = None
        self.result_found_at: SearchResult = result_found_at

    def __repr__(self) -> str:
        if isinstance(self.parsed_argument, Exception):
            return f"<Failed Token {type(self).__name__} argument={self.argument!r} error={self.parsed_argument!r} span=({(self.start, self.stop)}>"
        elif self.parsed_argument is not None:
            return f"<Token {type(self).__name__} argument={self.invoked_with}:{str(self.parsed_argument)!r}>"
        else:
            return f"<Uninitiated Token {type(self).__name__} argument={self.argument!r} span=({(self.start, self.stop)}>"

    def check(self, message: discord.Message):
        return NotImplemented

    async def parse(self, ctx: DuckContext):
        if self.converter is NotImplemented:
            raise RuntimeError('No converter given for Token %s' % type(self).__name__)
        try:
            self.parsed_argument = await commands.run_converters(
                ctx,
                self.converter,
                self.argument.strip(),
                commands.Parameter(
                    self.invoked_with,
                    kind=inspect._ParameterKind.POSITIONAL_ONLY,
                    annotation=self.converter,
                ),
            )
            self.validate()

        except Exception as e:
            self.parsed_argument = e
            raise TokenParsingError(self, e)

    def validate(self):
        return True


class FromUser(Token):
    name = 'from'
    converter = Union[discord.Member, discord.User]

    def check(self, message: discord.Message):
        return message.author == self.parsed_argument


class MentionsUser(FromUser):
    name = 'mentions'

    def check(self, message: discord.Message):
        return self.parsed_argument in message.mentions


class HasPartOfAMessage(Token):
    name = 'has'
    converter = Literal[
        'link',
        'links',
        'embed',
        'embeds',
        'file',
        'files',
        'video',
        'image',
        'images',
        'sound',
        'sounds',
        'sticker',
        'stickers',
        'reaction',
        'reactions',
        'emoji',
        'emojis',
    ]

    def check(self, message: discord.Message):
        match self.parsed_argument:
            case 'link' | 'links':
                return URL_REGEX.search(message.content) is not None
            case 'embed' | 'embeds':
                return bool(message.embeds)
            case 'file' | 'files':
                return bool(message.attachments)
            case 'video':
                return any((att.content_type or '').startswith('video/') for att in message.attachments)
            case 'image' | 'images':
                return any((att.content_type or '').startswith('image/') for att in message.attachments)
            case 'sound' | 'sounds':
                return any((att.content_type or '').startswith('audio/') for att in message.attachments)
            case 'sticker' | 'stickers':
                return bool(message.stickers)
            case 'reaction' | 'reactions':
                return bool(message.reactions)
            case 'emoji' | 'emojis':
                return EMOJI_REGEX.search(message.content) is not None
            case _:
                return False


class IsATypeOfUser(Token):
    name = 'is'
    converter = Literal['bot', 'human', 'user', 'webhook']

    def check(self, message: discord.Message):
        match self.parsed_argument:
            case 'bot':
                return message.author.bot
            case 'human' | 'user':
                return not message.author.bot
            case 'webhook':
                return message.webhook_id is not None


class DateDeterminer(Token):
    name = ('before', 'after', 'around', 'during')
    converter = discord.Object
    parsed_argument: discord.Object

    def _around_strategy(self, a: datetime.datetime, b: datetime.datetime):
        return a.year == b.year and a.month == b.month and a.day == b.day

    def check(self, message: discord.Message):
        return True  # this will use the before and after arguments on Channel.purge

    async def parse(self, ctx: DuckContext):
        if self.invoked_with == 'during':
            self.invoked_with = 'around'
        return await super().parse(ctx)

    def validate(self):
        # this is a special parameter which will be passed directly to history()
        # so we need to do extra checking to ensure that this is used properly, and
        # in a non-confusing way. Disallowing `X or before:` and so on, and also disallowing
        # this token to be put within a parentheses.
        result = self.result_found_at

        if result != result.root_parent:
            raise commands.CommandError('`before:`, `after:` and `around:` must not be grouped within parentheses.')

        from .parser import Separator  # Avoid circular imports

        for predicate in result.predicates:
            if predicate is Separator.OR:
                raise commands.CommandError(
                    'When using `before:`, `after:` or `around:`, you cannot use `or` to separate the different search terms.\n'
                    'For example: `from: @user around: <message ID>` is valid, so is `around: <message ID> '
                    '(from: user or has: image)`. But the following is not: `from: @user or around: <message ID>`'
                )

            elif predicate is self:
                continue  # we found ourselves.

            elif isinstance(predicate, DateDeterminer):
                if predicate.invoked_with == self.invoked_with:
                    raise commands.CommandError(f'You have already used `{self.invoked_with}:` once before')

                elif self.invoked_with in ('around', 'during'):
                    raise commands.CommandError('When using `around:` you cannot specify `before:` or `after:`')
        return True


class ContainsSubstring(Token):
    name = ('contains', 'prefix', 'suffix')
    converter = str

    def check(self, message: discord.Message):
        match self.invoked_with:
            case 'contains':
                return self.parsed_argument in message.content
            case 'prefix':
                return message.content.startswith(self.parsed_argument)
            case 'suffix':
                return message.content.endswith(self.parsed_argument)

    def validate(self):
        if not self.argument.strip():
            raise commands.BadArgument(f"`{self.invoked_with}:` cannot have an empty string.")


class Pinned(Token):
    name = 'pinned'
    converter = bool

    def check(self, message: discord.Message):
        return message.pinned == self.parsed_argument


ALL_TOKENS: List[Type[Token]] = [FromUser, MentionsUser, HasPartOfAMessage, IsATypeOfUser, DateDeterminer, ContainsSubstring]
# Remember to update the doc-string of `purge` in `../cog.py`
