from __future__ import annotations

import asyncio
import contextlib
import inspect
import io
import typing
from collections import defaultdict
from typing import Optional, Union, Type, List, TypeVar, Callable

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import DuckCog, DuckContext, ViewMenuPages, group, StringTranslatedCommandError
from utils import TranslatedEmbed, FormatString

T = TypeVar('T')
CO_T = TypeVar("CO_T", bound='Union[Type[commands.Converter], commands.Converter]')
AWARD_EMOJI = [chr(i) for i in range(129351, 129351 + 3)] + ['\N{SPORTS MEDAL}'] * 2


def copy_doc(original: Callable) -> Callable[[T], T]:
    def decorator(overridden: T) -> T:
        overridden.__doc__ = original.__doc__
        return overridden
    return decorator


class Tag:
    """
    Represents a tag.

    Attributes
    ----------
    id: int
        The ID of the tag.
    name: str
        The name of the tag.
    content: str
        The content of the tag.
    embed: Optional[discord.Embed]
        The embed of the tag.
    owner_id: int
        The ID of the owner of the tag.
    """
    __slots__ = ("name", "content", "embed", "id", "owner_id", "guild_id", "_cs_raw")

    def __init__(self, payload: dict):
        self.id: int = payload["id"]
        self.name: str = payload["name"]
        self.content: str = payload["content"]

        self.embed: Optional[discord.Embed]
        if embed := payload["embed"]:
            self.embed = discord.Embed.from_dict(embed)
        else:
            self.embed = None

        self.owner_id: int = payload["owner_id"]
        self.guild_id: int = payload["guild_id"]

    @discord.utils.cached_slot_property('_cs_raw')
    def raw(self):
        r = discord.utils.escape_markdown(self.content)
        return r.replace('<', '\\<')

    @property
    def is_global(self):
        """ bool: Whether the tag is global or not. """
        return self.guild_id is None

    async def edit(
            self,
            connection: typing.Union[asyncpg.Connection, asyncpg.Pool],
            content: Union[str, commands.clean_content],
            embed: Optional[discord.Embed] = discord.utils.MISSING
    ) -> None:
        """|coro|

        Edits the tag's content and embed.

        Parameters
        ----------
        content: Union[str, commands.clean_content]
            The new content of the tag.
        embed: Optional[discord.Embed]
            The new embed of the tag.
            If None, the embed will be removed.
        connection: Union[asyncpg.Connection, asyncpg.Pool]
            The connection to use.
        """
        if embed is not discord.utils.MISSING:
            embed = embed.to_dict() if embed else None  # type: ignore
            query = "UPDATE tags SET content = $1, embed = $2 WHERE id = $3"
            args = (content, embed, self.id)

            def update():
                self.content = content  # type: ignore
                self.embed = embed
        else:
            query = "UPDATE tags SET content = $1 WHERE id = $2"
            args = (content, self.id)

            def update():
                self.content = content  # type: ignore

        await connection.execute(query, *args)
        update()

    async def transfer(self, connection: typing.Union[asyncpg.Connection, asyncpg.Pool], user: discord.Member):
        """|coro|

        Transfers the tag to another user.

        Parameters
        ----------
        user: discord.User
            The user to transfer the tag to.
        connection: Union[asyncpg.Connection, asyncpg.Pool]
            The connection to use.
        """
        query = "UPDATE tags SET owner_id = $1 WHERE id = $2"
        await connection.execute(query, user.id, self.id)
        self.owner_id = user.id

    async def delete(self, connection: typing.Union[asyncpg.Connection, asyncpg.Pool]):
        """|coro|

        Deletes the tag.

        Parameters
        ----------
        connection: Union[asyncpg.Connection, asyncpg.Pool]
            The connection to use.
        """
        query = "DELETE FROM tags WHERE id = $1"
        await connection.execute(query, self.id)

    async def use(self, connection: typing.Union[asyncpg.Connection, asyncpg.Pool]):
        """|coro|

        Adds one to the tag's usage count.

        Parameters
        ----------
        connection: Union[asyncpg.Connection, asyncpg.Pool]
            The connection to use.
        """
        query = "UPDATE tags SET uses = uses + 1 WHERE id = $1"
        await connection.execute(query, self.id)

    async def add_alias(
            self,
            connection: typing.Union[asyncpg.Connection, asyncpg.Pool],
            alias: typing.Union[str, TagName],
            user: discord.User | discord.Member,
    ):
        """|coro|

        Adds an alias to the tag.

        Parameters
        ----------
        alias: Union[str, TagName]
            The alias to add.
        user: discord.User
            The user who added the alias.
        connection: Union[asyncpg.Connection, asyncpg.Pool]
            The connection to use.
        """
        query = "INSERT INTO tags (name, owner_id, guild_id, points_to) VALUES " \
                "($1, $2, (SELECT guild_id FROM tags WHERE id = $3), $3)"
        await connection.execute(query, alias, user.id, self.id)


# noinspection PyShadowingBuiltins
class UnknownUser(discord.Object):
    # noinspection PyPep8Naming
    class display_avatar:
        url = "https://cdn.discordapp.com/embed/avatars/0.png"

    def __init__(self, id: int):
        super().__init__(id=id)

    def __str__(self):
        return "@Unknown User#0000"

    @property
    def mention(self):
        return "<@{}>".format(self.id)


class TagName(commands.clean_content):
    def __init__(self, *, lower=True):
        self.lower = lower
        super().__init__()
    
    def __class_getitem__(cls, attr: bool):
        if not isinstance(attr, bool):
            raise TypeError("Expected bool, not {}".format(type(attr).__name__))
        return TagName(lower=attr)

    # Taken from R.Danny's code because I'm lazy
    async def actual_conversion(self, converted, error: Type[discord.DiscordException], bot):
        """ The actual conversion function after clean content has done its job. """
        lower = converted.lower().strip()

        if not lower:
            raise error('Missing tag name.')

        if len(lower) > 200:
            raise error('Tag name is a maximum of 200 characters.')

        first_word, _, _ = lower.partition(' ')

        # get tag command.
        root = bot.get_command('tag')
        if first_word in root.all_commands:
            raise error('This tag name starts with a reserved word.')

        return converted if not self.lower else lower

    # msg commands
    async def convert(self, ctx, argument):
        converted = await super().convert(ctx, argument)
        return await self.actual_conversion(converted, commands.BadArgument, ctx.bot)


class TagsFromFetchedPageSource(menus.ListPageSource):
    def __init__(self, tags: typing.List[asyncpg.Record], *, per_page: int = 10,
                 member: discord.Member | discord.User | None = None, ctx: DuckContext):
        super().__init__(tags, per_page=per_page)
        self.member = member
        self.ctx = ctx

    async def format_page(self, menu: menus.MenuPages, entries: typing.List[asyncpg.Record]):
        source = enumerate(entries, start=menu.current_page * self.per_page + 1)
        formatted = '\n'.join(f"{idx}. {tag['name']} (ID: {tag['id']})" for idx, tag in source)
        embed = TranslatedEmbed(title=38, description=formatted, colour=self.ctx.bot.colour)
        if self.member:
            embed.set_author(name=str(self.member), icon_url=self.member.display_avatar.url)
        embed.set_footer(text=FormatString(39, menu.current_page + 1, self.get_max_pages(), len(self.entries)))
        return embed


class Tags(DuckCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tags_in_progress = defaultdict(set)

    @staticmethod
    def maybe_file(text: str, *, filename='tag') -> dict:
        """ Checks if text is greater than 2000 characters

        Parameters
        ----------
        text: str
            The text to check.
        filename: str
            The filename to use.
            Defaults to 'tag'.

        Returns
        -------
        dict
            The file object.
        """
        if len(text) > 2000:
            return {"file": discord.File(io.BytesIO(text.encode()), filename=f"{filename}.txt")}
        return {"content": text}

    @staticmethod
    def maybe_codeblock(content: str | None = None, file: discord.File | None = None, *, filename='tag') -> dict:
        """ Maybe puts `text` in a code block.

        **Example**

        .. code-block:: python3
            await ctx.send(**self.maybe_codeblock(**self.maybe_file(text)))
            # or
            await ctx.send(**self.maybe_codeblock(content=text))

        Parameters
        ----------
        content: str
            The text to check.
        file: discord.File``
            The file to check.
        filename: str
            The filename to use.
            Defaults to 'tag'.

        Returns
        -------
        str
            The formatted text.
        """
        if content and len(content) <= 1992:
            return {'content': f"```\n{content}\n```"}
        elif content:
            return {'file': discord.File(io.BytesIO(content.encode()), filename="tag.txt")}
        else:
            return {'file': file}

    async def get_tag(
            self,
            tag: Union[str, commands.clean_content],
            guild_id: Optional[int],
            *,
            find_global: bool = False,
            connection: Optional[Union[asyncpg.Connection, asyncpg.Pool]] = None
    ) -> Tag:
        """|coro|

        Gets a tag

        Parameters
        ----------
        tag: str
            The tag to get
        guild_id: int
            The guild id to get the tag from. If
            None, the tag will be retrieved from
            the global tags.
        find_global: bool
            Whether to search the global tags.
            Defaults to False.
        connection: Optional[Union[asyncpg.Connection, asyncpg.Pool]]
            The connection to use. If None,
            the bot's pool will be used.

        Returns
        -------
        Tag
            The tag.
        """
        connection = connection or self.bot.pool
        if find_global is not True:
            query = """
                SELECT id, name, content, embed, owner_id, guild_id FROM tags 
                WHERE (LOWER(name) = LOWER($1::TEXT) and (guild_id = $2) and (content is not null)) 
                OR (id = (
                    SELECT points_to FROM tags 
                        WHERE LOWER(name) = LOWER($1::TEXT) 
                        AND guild_id = $2 
                        AND points_to IS NOT NULL
                    ))
                LIMIT 1 -- just in case
            """
        else:
            query = """
                SELECT id, name, content, embed, owner_id, guild_id FROM tags 
                WHERE (LOWER(name) = LOWER($1::TEXT) and (guild_id IS NULL or guild_id = $2) and (content is not null))
                OR (id = (
                    SELECT points_to FROM tags 
                        WHERE LOWER(name) = LOWER($1::TEXT)
                        AND (guild_id IS NULL OR guild_id = $2) 
                        AND points_to IS NOT NULL
                    ))
                ORDER BY guild_id
                    -- if global, we want local tags to 
                    -- take priority.
                LIMIT 1
                    -- when there are global and local
            """

        fetched_tag = await connection.fetchrow(query, tag, guild_id)
        if fetched_tag is None:
            if find_global:
                query = """
                    SELECT name FROM tags
                    WHERE (guild_id = $1 OR guild_id IS NULL) 
                    AND LOWER(name) % LOWER($2::TEXT)
                    ORDER BY similarity(name, $2) DESC
                    LIMIT 3
                """
            else:
                query = """
                    SELECT name FROM tags
                    WHERE guild_id = $1 
                    AND LOWER(name) % LOWER($2::TEXT)
                    ORDER BY similarity(name, $2) DESC
                    LIMIT 3
                """
            similar = await connection.fetch(query, guild_id, tag)
            if not similar:
                raise commands.BadArgument(f"Tag not found.")
            joined = '\n'.join(r['name'] for r in similar)
            raise commands.BadArgument(f"Tag not found. Did you mean...\n{joined}")

        return Tag(fetched_tag)

    @contextlib.contextmanager
    def reserve_tag(self, name, guild_id):
        """ Simple context manager to reserve a tag. """
        if name in self._tags_in_progress[guild_id]:
            raise commands.BadArgument("Sorry, this tag is already being created!")
        try:
            self._tags_in_progress[guild_id].add(name)
            yield None
        finally:
            self._tags_in_progress[guild_id].discard(name)

    async def make_tag(
            self,
            guild: Optional[discord.Guild],
            owner: Union[discord.User, discord.Member],
            tag: Union[str, commands.clean_content],
            content: Union[str, commands.clean_content],
    ) -> Tag:
        """|coro|

        Creates a tag.

        Parameters
        ----------
        guild: Optional[discord.Guild]
            The guild the tag will be bound to.
        owner: Union[discord.User, discord.Member]
            The owner of the tag.
        tag: Union[str, TagName]
            The name of the tag.
        content: Union[str, commands.clean_content]
            The content of the tag.

        Returns
        -------
        Tag
            The tag.
        """
        with self.reserve_tag(tag, guild.id if guild else None):
            try:
                async with self.bot.safe_connection() as conn:
                    stuff = await conn.fetchrow("""
                        INSERT INTO tags (name, content, guild_id, owner_id) VALUES ($1, $2, $3, $4)
                        RETURNING id, name, content, embed, owner_id, guild_id
                    """, tag, content, guild.id if guild else None, owner.id)
                    return Tag(stuff)
            except asyncpg.UniqueViolationError:
                raise StringTranslatedCommandError(3)
            except asyncpg.StringDataRightTruncationError:
                raise StringTranslatedCommandError(4)
            except asyncpg.CheckViolationError:
                raise StringTranslatedCommandError(5)
            except Exception as e:
                await self.bot.exceptions.add_error(error=e)
                raise StringTranslatedCommandError(6)

    async def wait_for(
            self,
            channel: discord.abc.MessageableChannel,
            author: discord.Member | discord.User,
            *,
            timeout: int = 60,
            converter: CO_T | Type[CO_T] | None = None,
            ctx: DuckContext | None = None
    ) -> Union[str, CO_T]:
        """|coro|

        Waits for a message to be sent in a channel.

        Parameters
        ----------
        channel: discord.TextChannel
            The channel to wait for a message in.
        author: discord.Member
            The member to wait for a message from.
        timeout: int
            The timeout in seconds. Defaults to 60.
        converter: commands.Converter
            The converter to use. Defaults to None.
        ctx: commands.Context
            The context to use for the converter, if passed.
        """
        try:
            def check(msg: discord.Message):
                return msg.channel == channel and msg.author == author

            message: discord.Message = await self.bot.wait_for('message', timeout=timeout, check=check)

            if converter is not None:
                try:
                    if inspect.isclass(converter) and issubclass(converter, commands.Converter):
                        if inspect.ismethod(converter.convert):
                            content = await converter.convert(ctx, message.content)
                        else:
                            content = await converter().convert(ctx, message.content)  # type: ignore
                    elif isinstance(converter, commands.Converter):
                        content = await converter.convert(ctx, message.content)  # type: ignore
                    else:
                        content = message.content
                except commands.CommandError:
                    raise
                except Exception as exc:
                    raise commands.ConversionError(converter, exc) from exc  # type: ignore
            else:
                content = message.content

            if not content:
                raise StringTranslatedCommandError(5)
            if isinstance(content, str) and len(content) > 2000:
                raise StringTranslatedCommandError(1)
            return content
        except asyncio.TimeoutError:
            raise StringTranslatedCommandError(7, f"{str(author)}")

    async def __tag(self, ctx: commands.Context, name: TagName, *, guild: discord.Guild | None):
        """|coro|

        Base tags command. Also shows a tag.

        Parameters
        ----------
        name: str
            The tag to show
        """
        tag = await self.get_tag(name, guild.id if guild else None, find_global=True)
        print(tag.id)
        if tag.embed and ctx.channel.permissions_for(ctx.me).embed_links:  # type: ignore
            await ctx.channel.send(tag.content, embed=tag.embed)
        else:
            await ctx.channel.send(tag.content)
        await tag.use(self.bot.pool)

    @group(name='tag', invoke_without_command=True)
    @copy_doc(__tag)
    async def tag(self, ctx: DuckContext, *, name: TagName):
        await self.__tag(ctx, name, guild=ctx.guild)

    @tag.group(name='global', invoke_without_command=True)
    @copy_doc(__tag)
    async def tag_global(self, ctx: DuckContext, name: TagName):
        await self.__tag(ctx, name, guild=None)

    async def __tag_create(self, ctx: DuckContext, tag: TagName,
                           content: commands.clean_content, guild: discord.Guild | None):
        """|coro|

        Creates a tag

        Parameters
        ----------
        tag: str
            The tag to create
        content: str
            The content of the tag
        """
        if len(str(content)) > 2000:
            raise StringTranslatedCommandError(1)
        tag_ = await self.make_tag(guild, ctx.author, tag, content)
        await ctx.send(2, f"{tag_.name!r}")

    @tag.command(name='create', aliases=['new', 'add'])
    @copy_doc(__tag_create)
    async def tag_create(self, ctx: DuckContext, tag: TagName(lower=False), *, content: commands.clean_content):  # type: ignore
        await self.__tag_create(ctx, tag, content, guild=ctx.guild)

    @tag_global.command(name='create', aliases=['new', 'add'])
    @copy_doc(__tag_create)
    async def tag_global_create(self, ctx: DuckContext, tag: TagName(lower=False), *, content: commands.clean_content):  # type: ignore
        await self.__tag_create(ctx, tag, content, guild=None)

    async def __tag_make(self, ctx: DuckContext, guild: discord.Guild | None):
        """|coro|

        Interactive prompt to make a tag.
        """
        await ctx.send(8)
        try:
            name = await self.wait_for(ctx.channel, ctx.author, converter=TagName(lower=False), ctx=ctx)
        except commands.BadArgument as e:
            cmd = f"{ctx.clean_prefix}{ctx.command.qualified_name if ctx.command else '<Unknown Command>'}"
            raise StringTranslatedCommandError(9, e, f"{cmd!r}")

        args = (name, guild.id if guild else 0)
        with self.reserve_tag(*args):
            query = """
                SELECT EXISTS(
                    SELECT * FROM tags
                    WHERE name = $1
                    AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
                )
            """
            check = await self.bot.pool.fetchval(query, *args)
            if check:
                cmd = f"{ctx.clean_prefix}{ctx.command.qualified_name if ctx.command else '<Unknown Command>'}"
                raise StringTranslatedCommandError(9, await ctx.translate(3), f"{cmd!r}")
            await ctx.send(10)
            content = await self.wait_for(ctx.channel, ctx.author,
                                          converter=commands.clean_content,
                                          ctx=ctx, timeout=60 * 10)

        await self.make_tag(guild, ctx.author, name, content)
        await ctx.send(2, f"{name!r}")

    @tag.command(name='make', ignore_extra=False)
    @copy_doc(__tag_make)
    @commands.max_concurrency(1, commands.BucketType.member)
    async def tag_make(self, ctx: DuckContext):
        await self.__tag_make(ctx, ctx.guild)

    @tag_global.command(name='make', ignore_extra=False)
    @copy_doc(__tag_make)
    @commands.max_concurrency(1, commands.BucketType.member)
    async def tag_global_make(self, ctx: DuckContext):
        await self.__tag_make(ctx, None)

    @tag.command(name='claim')  # no global for you! :P
    async def tag_claim(self, ctx: DuckContext, name: TagName):
        """|coro|

        Claims a tag from a user that isn't
        in this server anymore.

        Parameters
        ----------
        name: str
            The name of the tag to claim
        """
        tag = await self.get_tag(name, ctx.guild.id)
        user = await self.bot.get_or_fetch_member(guild=ctx.guild, user=tag.owner_id)
        if user:
            await ctx.send(11)
            return
        assert isinstance(ctx.author, discord.Member)
        await tag.transfer(self.bot.pool, ctx.author)
        await ctx.send(12, f"{name!r}")

    async def __tag_edit(self, ctx: DuckContext, tag_name: TagName, content: commands.clean_content,
                         guild: discord.Guild | None):
        """|coro|

        Edits a tag

        Parameters
        ----------
        tag: str
            The tag to edit
        content: str
            The new content of the tag
        """
        async with self.bot.safe_connection() as conn:
            tag = await self.get_tag(tag_name, guild.id if guild else None, connection=conn, find_global=guild is None)
            if tag.owner_id != ctx.author.id:
                raise StringTranslatedCommandError(13)
            await tag.edit(conn, content)
        await ctx.send(14)

    @tag.command(name='edit')
    @copy_doc(__tag_edit)
    async def tag_edit(self, ctx: DuckContext, tag: TagName, *, content: commands.clean_content):
        await self.__tag_edit(ctx, tag, content, ctx.guild)

    @tag_global.command(name='edit')
    @copy_doc(__tag_edit)
    async def tag_global_edit(self, ctx: DuckContext, tag: TagName, *, content: commands.clean_content):
        await self.__tag_edit(ctx, tag, content, ctx.guild)

    async def __tag_append(self, ctx: DuckContext, tag: TagName, content: commands.clean_content,
                           guild: discord.Guild | None):
        """|coro|

        Appends content to a tag.
        This will add a new line before the content being appended.

        Parameters
        ----------
        tag: str
            The tag to append to
        content: str
            The content to append
        """
        async with self.bot.safe_connection() as conn:
            query = """
                WITH edited AS (
                    UPDATE tags
                    SET content = content || E'\n' || $1
                    WHERE name = $2
                    AND CASE WHEN ( $3::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $3 ) END
                    AND owner_id = $4
                    RETURNING *
                )
                SELECT EXISTS ( SELECT * FROM edited )
            """
            confirm = await conn.fetchval(query, content, tag, guild.id if guild else 0, ctx.author.id)
            if confirm:
                await ctx.send(14)
            else:
                await ctx.send(13)

    @tag.command(name='append')
    @copy_doc(__tag_append)
    async def tag_append(self, ctx: DuckContext, tag: TagName, *, content: commands.clean_content):
        await self.__tag_append(ctx, tag, content, ctx.guild)

    @tag_global.command(name='append')
    @copy_doc(__tag_append)
    async def tag_global_append(self, ctx: DuckContext, tag: TagName, *, content: commands.clean_content):
        await self.__tag_append(ctx, tag, content, ctx.guild)

    async def __tag_delete(self, ctx: DuckContext, tag: TagName, guild: discord.Guild | None):
        """|coro|

        Deletes one of your tags.

        Parameters
        ----------
        tag: str
            The name of the tag to delete
        """
        async with self.bot.safe_connection() as conn:
            query = """
                WITH deleted AS (
                    DELETE FROM tags
                        WHERE LOWER(name) = LOWER($1::TEXT)
                        AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
                        AND (owner_id = $3 OR $4::BOOL = TRUE)
                            -- $4 will be true for moderators.
                        RETURNING name, points_to
                )
                SELECT deleted.name, (
                    SELECT name
                        FROM tags
                        WHERE id = (deleted.points_to)
                ) AS parent
                FROM deleted
            """

            is_mod = await self.bot.is_owner(ctx.author)

            if guild and isinstance(ctx.author, discord.Member):
                is_mod = is_mod or ctx.author.guild_permissions.manage_messages

            tag_p = await conn.fetchrow(query, tag, guild.id if guild else 0, ctx.author.id, is_mod)

            if tag_p is None:
                await ctx.send(15 if is_mod else 16)
            elif tag_p['parent'] is not None:
                await ctx.send(17, tag_p['name'], tag_p['parent'])
            else:
                await ctx.send(18, tag_p['name'])

    @tag.command(name='delete')
    @copy_doc(__tag_delete)
    async def tag_delete(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_delete(ctx, tag, ctx.guild)

    @tag_global.command(name='delete')
    @copy_doc(__tag_delete)
    @commands.is_owner()
    async def tag_global_delete(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_delete(ctx, tag, None)

    async def __tag_delete_id(self, ctx: DuckContext, tag_id: int, guild: discord.Guild | None):
        """|coro|

        Deletes a tag by ID.

        Parameters
        ----------
        tag_id: int
            the ID of the tag.
        """
        async with self.bot.safe_connection() as conn:
            query = """
                WITH deleted AS (
                    DELETE FROM tags
                        WHERE id = $1
                        AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
                        AND (owner_id = $3 OR $4::BOOL = TRUE)
                            -- $4 will be true for moderators.
                        RETURNING name, points_to
                )
                SELECT deleted.name, (
                    SELECT name
                        FROM tags
                        WHERE id = (deleted.points_to)
                ) AS parent
                FROM deleted
            """

            is_mod = await self.bot.is_owner(ctx.author)

            if guild and isinstance(ctx.author, discord.Member):
                is_mod = is_mod or ctx.author.guild_permissions.manage_messages

            tag_p = await conn.fetchrow(query, tag_id, guild.id if guild else 0, ctx.author.id, is_mod)

            if tag_p is None:
                await ctx.send(15 if is_mod else 16)
            elif tag_p['parent'] is not None:
                await ctx.send(17)
            else:
                await ctx.send(18)

    @tag.command(name='delete-id')
    @copy_doc(__tag_delete_id)
    async def tag_delete_id(self, ctx: DuckContext, *, tag_id: int):
        await self.__tag_delete_id(ctx, tag_id, ctx.guild)

    @tag_global.command(name='delete-id')
    @copy_doc(__tag_delete_id)
    @commands.is_owner()
    async def tag_global_delete_id(self, ctx: DuckContext, *, tag_id: int):
        await self.__tag_delete_id(ctx, tag_id, None)

    async def __tag_purge(self, ctx: DuckContext, member: discord.Member | discord.User, guild: discord.Guild | None):
        """|coro|

        Purges all tags from a user.

        Parameters
        ----------
        member: discord.Member
            The user whose tags will be purged.
        """
        is_mod = await self.bot.is_owner(ctx.author)

        if guild:
            if not isinstance(ctx.author, discord.Member):
                raise commands.BadArgument('error!')
            is_mod = is_mod or ctx.author.guild_permissions.manage_messages

        if not is_mod:
            await ctx.send(19)
            return

        query = """
            SELECT COUNT(*) FROM tags 
            WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $1 ) END
            AND owner_id = $2
        """
        args = (guild.id if guild else 0, member.id)

        amount: int | None = self.bot.pool.fetchval(query, *args)  # type: ignore

        if amount == 0 or amount is None:
            await ctx.send(20, str(member))
            return

        result = await ctx.confirm(await ctx.translate(21, str(member), amount))

        if result is None:
            return
        elif result is False:
            await ctx.send(22)
            return

        async with self.bot.safe_connection() as conn:
            query = """
                WITH deleted AS (
                    DELETE FROM tags
                        WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
                        AND owner_id = $2
                        RETURNING name, points_to
                )
                SELECT COUNT(*) FROM deleted
            """

            tag_p = await conn.fetchval(query, guild.id if guild else 0, member.id)

            await ctx.send(23, member, tag_p)

    @tag.command(name='purge')
    @copy_doc(__tag_purge)
    async def tag_purge(self, ctx: DuckContext, member: typing.Union[discord.Member, discord.User]):
        await self.__tag_purge(ctx, member, ctx.guild)

    @tag_global.command(name='purge')
    @copy_doc(__tag_purge)
    @commands.is_owner()
    async def tag_global_purge(self, ctx: DuckContext, member: typing.Union[discord.Member, discord.User]):
        await self.__tag_purge(ctx, member, None)

    async def __tag_alias(self, ctx: DuckContext, alias: TagName, points_to: TagName, guild: discord.Guild | None):
        """|coro|

        Creates an alias for a tag.

        Parameters
        ----------
        alias: str
            The name of the alias
        points_to: str
            The name of the tag to point to
        """
        async with self.bot.safe_connection() as conn:
            try:
                tag = await self.get_tag(points_to, guild.id if guild else None, connection=conn, find_global=guild is None)
            except commands.BadArgument:
                return await ctx.send(24, f"{points_to!r}")
            try:
                await tag.add_alias(conn, alias, ctx.author)
            except asyncpg.UniqueViolationError:
                return await ctx.send(25)
            except Exception as e:
                await self.bot.exceptions.add_error(error=e, ctx=ctx)
                return await ctx.send(26)
            await ctx.send(27, f"{alias!r}", f"{points_to!r}")

    @tag.command(name='alias')
    @copy_doc(__tag_alias)
    async def tag_alias(self, ctx: DuckContext, alias: TagName, *, points_to: TagName):
        await self.__tag_alias(ctx, alias, points_to, ctx.guild)

    @tag_global.command(name='alias')
    @copy_doc(__tag_alias)
    async def tag_global_alias(self, ctx: DuckContext, alias: TagName, *, points_to: TagName):
        await self.__tag_alias(ctx, alias, points_to, None)

    async def __tag_info(self, ctx: DuckContext, tag: TagName, guild: discord.Guild | None):
        """|coro|

        Gets information about a tag

        Parameters
        ----------
        tag: str
            The name of the tag to get information about
        """
        query = """
            WITH original_tag AS (
                SELECT * FROM tags
                WHERE LOWER(name) = LOWER($1::TEXT)
                AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
            )

            SELECT 
                original_tag.name,
                original_tag.owner_id,
                original_tag.created_at,
                (original_tag.points_to IS NOT NULL) as is_alias,
                (SELECT tags.name FROM tags WHERE tags.id = original_tag.points_to) AS parent,
                uses,
                (CASE WHEN ( original_tag.points_to IS NULL ) THEN ( 
                SELECT COUNT(*) FROM tags WHERE tags.points_to = original_tag.id ) END ) AS aliases
            FROM original_tag
        """
        args = (query, tag, guild.id if guild else 0)
        name, owner_id, created_at, is_alias, parent, uses, aliases_amount = await self.bot.pool.fetchrow(*args)
        owner = await self.bot.get_or_fetch_user(owner_id) or UnknownUser(owner_id)

        # TODO: Add a way to translate embeds.
        embed = TranslatedEmbed(title=name, timestamp=created_at)
        embed.set_author(name=str(owner), icon_url=owner.display_avatar.url)
        embed.add_field(name=28, value=f'{owner.mention}')
        if is_alias:
            embed.add_field(name=29, value=parent)
            embed.set_footer(text=30)
        else:
            embed.add_field(name=31, value=str(uses))
            embed.add_field(name=32, value=FormatString(33, aliases_amount), inline=False)
            embed.set_footer(text=34)
        await ctx.send(embed=embed)

    @tag.command(name='info', aliases=['owner'])
    @copy_doc(__tag_info)
    async def tag_info(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_info(ctx, tag, ctx.guild)

    @tag_global.command(name='info')
    @copy_doc(__tag_info)
    async def tag_global_info(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_info(ctx, tag, None)

    async def __tag_list(self, ctx: DuckContext, member: discord.Member | discord.User | None, guild: discord.Guild | None):
        """|coro|

        Lists all tags owned by a member.

        Parameters
        ----------
        member: discord.Member
            The member to list tags for. Defaults to the author of the command.
        """
        query = """
            SELECT name, id FROM tags
            WHERE CASE WHEN ( $1::BIGINT = 0 ) 
                        THEN ( guild_id IS NULL ) 
                        ELSE ( guild_id = $1 ) END
            AND ( owner_id = $2 OR $2::BIGINT = 0 )
            ORDER BY name
        """
        args = (guild.id if guild else 0, member.id if member else 0)
        tags = await self.bot.pool.fetch(query, *args)

        if not tags:
            return await ctx.send((35 if guild else 36) if not member else FormatString(37, str(member)))

        paginator = ViewMenuPages(
            source=TagsFromFetchedPageSource(tags, member=member, ctx=ctx),
            ctx=ctx)
        await paginator.start()

    @tag.command(name='list')
    @copy_doc(__tag_list)
    async def tag_list(self, ctx: DuckContext, *, member: Optional[discord.Member] = None):
        await self.__tag_list(ctx, member, ctx.guild)

    @tag_global.command(name='list')
    @copy_doc(__tag_list)
    async def tag_global_list(self, ctx: DuckContext, *, user:  Optional[discord.User] = None):
        await self.__tag_list(ctx, user, None)

    async def __tag_search(self, ctx: DuckContext, query: str, guild: discord.Guild | None):
        """|coro|

        Searches for tags.

        Parameters
        ----------
        query: str
            The query to search for.
        """
        db_query = """
            SELECT name, id FROM tags
            WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $1 ) END
            AND similarity(name, $2) > 0
            ORDER BY similarity(name, $2) DESC
            LIMIT 200
        """
        args = (guild.id if guild else 0, query)
        tags = await self.bot.pool.fetch(db_query, *args)
        if not tags:
            return await ctx.send(40)

        paginator = ViewMenuPages(
            source=TagsFromFetchedPageSource(tags, member=None, ctx=ctx),
            ctx=ctx)
        await paginator.start()

    @tag.command(name='search')
    @copy_doc(__tag_search)
    async def tag_search(self, ctx: DuckContext, *, query: str):
        await self.__tag_search(ctx, query, ctx.guild)

    @tag_global.command(name='search')
    @copy_doc(__tag_search)
    async def tag_global_search(self, ctx: DuckContext, *, query: str):
        await self.__tag_search(ctx, query, None)

    async def __tag_raw(self, ctx: DuckContext, tag_name: TagName, guild: discord.Guild | None):
        """|coro|

        Sends a raw tag.

        Parameters
        ----------
        tag: TagName
            The tag.
        """
        tag = await self.get_tag(tag_name, guild.id if guild else None, find_global=guild is None)
        await ctx.send(**self.maybe_file(tag.raw))

    @tag.command(name='raw')
    @copy_doc(__tag_raw)
    async def tag_raw(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_raw(ctx, tag, ctx.guild)

    @tag_global.command(name='raw')
    @copy_doc(__tag_raw)
    async def tag_global_raw(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_raw(ctx, tag, None)

    async def get_guild_or_global_stats(self, ctx: DuckContext, guild: discord.Guild | None, embed: TranslatedEmbed):
        """|coro|

        Gets the tag stats of a guild.

        Parameters
        ----------
        ctx: DuckContext
            The context of the command.
        guild: discord.Guild
            The guild to get the tag stats of.
            If ``None``, gets the global tag stats.
        embed: discord.Embed
            The base embed.
        """

        guild_id = guild.id if guild else 0

        # Top tags

        query = """
            SELECT name, uses,
            COUNT(*) OVER () AS total_tags,
            SUM(uses) OVER () AS total_uses
            FROM tags
            WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $1 ) END
            ORDER BY uses DESC
            LIMIT 5;
            """
        data = await self.bot.pool.fetch(query, guild_id)

        embed.description = FormatString(41, data[0]['total_tags'], data[0]['total_uses']) \
            if data else 42

        top_tags = [await ctx.translate(43, AWARD_EMOJI[index], name, uses)
                    for index, (name, uses, _, _) in enumerate(data)]

        embed.add_field(name=56, value='\n'.join(top_tags) or '\u200b', inline=False)

        # Top creators

        query = """
            SELECT COUNT(*) as tag_amount, owner_id
            FROM tags WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $1 ) END
            GROUP BY owner_id
            ORDER BY tag_amount DESC
            LIMIT 5;
            """

        data = await self.bot.pool.fetch(query, guild_id)

        top_creators = [await ctx.translate(44, AWARD_EMOJI[index], owner_id ,tag_amount)
                        for index, (tag_amount, owner_id) in enumerate(data)]

        embed.add_field(name=45, value='\n'.join(top_creators) or '\u200b', inline=False)

        # Top users

        query = """
            SELECT COUNT(*) as tag_amount, user_id
            FROM commands WHERE CASE WHEN ( $1::BIGINT = 0 ) THEN ( TRUE ) ELSE ( guild_id = $1 ) END
            AND CASE WHEN ( $1::BIGINT = 0 ) THEN ( command = 'tag global' ) ELSE ( command = 'tag' ) END
            GROUP BY user_id
            ORDER BY tag_amount DESC
            LIMIT 5;
            """

        data = await self.bot.pool.fetch(query, guild_id)

        top_users = [await ctx.translate(46, AWARD_EMOJI[index], user_id, tag_amount)
                     for index, (tag_amount, user_id) in enumerate(data)]

        embed.add_field(name=47, value='\n'.join(top_users) or '\u200b', inline=False)

        await ctx.send(embed=embed)

    async def user_tag_stats(self, ctx: DuckContext, member: discord.Member | discord.User,
                             guild: discord.Guild | None):
        """|coro|

        Gets the tag stats of a member.

        Parameters
        ----------
        ctx: DuckContext
            The context to get the number of tags in.
        member: discord.Member
            The member to get the stats for.
        guild: discord.Guild
            The guild to get the stats for.
            If ``None``, gets the global tag stats.
        """

        embed = TranslatedEmbed()
        embed.set_author(name=FormatString(48, str(ctx.author)), icon_url=member.display_avatar.url)
        args = (member.id, guild.id if guild else 0)

        # tags created

        query = """
            SELECT COUNT(*) as tag_amount,
            SUM(uses) as total_uses
            FROM tags WHERE owner_id = $1
            AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
            """
        data = await self.bot.pool.fetchrow(query, *args)

        if data:
            tags = f"{data['tag_amount']:,}"
            uses = f"{data['total_uses']:,}"
        else:
            tags = 'None'
            uses = 0

        embed.add_field(name=49, value=FormatString(50, tags), inline=False)
        embed.add_field(name=51, value=FormatString(52, uses), inline=False)

        # tags used

        query = """
            SELECT COUNT(*) as tag_amount
            FROM commands WHERE user_id = $1
            AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
            AND command = 'tag';
            """

        data = await self.bot.pool.fetchrow(query, *args)
        embed.add_field(name=55, value=FormatString(52, f"{data['tag_amount']:,}") if data else 'None', inline=False)

        # top tags
        query = """
            SELECT name, uses
            FROM tags WHERE owner_id = $1
            AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
            ORDER BY uses DESC
            LIMIT 5;
            """

        data = await self.bot.pool.fetch(query, *args)
        
        top_tags = [await ctx.translate(43, AWARD_EMOJI[index], name, uses)
                    for index, (name, uses) in enumerate(data)]

        embed.add_field(name=56, value='\n'.join(top_tags) or '\u200b', inline=False)

        await ctx.send(embed=embed)

    @tag.command(name='stats')
    async def tag_stats(self, ctx: DuckContext, member: Optional[discord.Member] = None):
        """|coro|

        Gets the tag stats of a member or this server.

        Parameters
        ----------
        member: discord.Member
            The member to get the stats for.
            If not specified, the stats of
            the server will be shown.
        """
        if member is None:
            embed = TranslatedEmbed()
            embed.set_author(name=FormatString(48, str(ctx.guild)),
                             icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await self.get_guild_or_global_stats(ctx, guild=ctx.guild, embed=embed)
        else:
            await self.user_tag_stats(ctx, member, ctx.guild)

    @tag_global.command(name='stats')
    async def tag_global_stats(self, ctx: DuckContext, user: Optional[discord.User] = None):
        """|coro|

        Gets the tag stats of a user or global.

        Parameters
        ----------
        user: discord.User
            The user to get the stats for.
            If not specified, the global
            stats will be shown.
        """
        if user is None:
            embed = TranslatedEmbed()
            embed.set_author(name=54,
                             icon_url=ctx.me.display_avatar.url)
            await self.get_guild_or_global_stats(ctx, guild=None, embed=embed)
        else:
            await self.user_tag_stats(ctx, user, None)

    async def __tag_remove_embed(self, ctx: DuckContext, tag: TagName, guild: discord.Guild | None = None):
        """|coro|

        Removes an embed from a tag. To add an embed, use the ``embed``. Example:
         ``[prefix] embed <flags> --save <tag name>`` where flags are the embed flags.
         See ``[prefix]embed --help`` for more information about the flags.

        Parameters
        ----------
        tag: TagName
            The name of the tag to remove the embed from.
        """
        query = """
            WITH updated AS (
                UPDATE tags SET embed = NULL
                WHERE name = $1 
                AND CASE WHEN ( $2::BIGINT = 0 ) THEN ( guild_id IS NULL ) ELSE ( guild_id = $2 ) END
                AND (owner_id = $3 or $4::bool = TRUE )
                    -- $4 will be true for moderators.
                RETURNING *
            )
            SELECT EXISTS ( SELECT * FROM updated )
        """
        is_mod = await self.bot.is_owner(ctx.author)

        if guild:
            if not isinstance(ctx.author, discord.Member):
                raise commands.BadArgument('error!')
            is_mod = is_mod or ctx.author.guild_permissions.manage_messages

        args = (tag, guild.id if guild else 0, ctx.author.id, is_mod)
        exists = await self.bot.pool.fetchval(query, *args)

        if not exists:
            StringTranslatedCommandError(13)
        await ctx.send(14)

    @tag.command(name='remove-embed')
    @copy_doc(__tag_remove_embed)
    async def tag_remove_embed(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_remove_embed(ctx, tag, ctx.guild)

    @tag_global.command(name='remove-embed')
    @copy_doc(__tag_remove_embed)
    async def tag_global_remove_embed(self, ctx: DuckContext, *, tag: TagName):
        await self.__tag_remove_embed(ctx, tag, None)

    @app_commands.command(name='tag')
    @app_commands.describe(
        tag_name='The tag to show.',
        ephemeral='Whether to show the tag only to you.',
        raw='Whether to show the raw tag.')
    @app_commands.rename(
        tag_name='tag-name',
        raw='raw-content')
    async def slash_tag(self, interaction: discord.Interaction, *, tag_name: str, ephemeral: Optional[bool] = None,
                        raw: Optional[typing.Literal['Yes', 'No', 'Send As File', 'Send Using Code Block']] = None):
        """ Shows a tag. For more commands, use the "tag" message command. """
        tag = await self.get_tag(tag_name, interaction.guild.id if interaction.guild else None, find_global=True)
        if raw == 'Yes':
            kwargs = {**self.maybe_file(tag.raw, filename=tag.name),
                      'ephemeral': True if ephemeral is None else ephemeral}
        elif raw == 'Send As File':
            kwargs = {'file': discord.File(io.BytesIO(tag.content.encode()), filename=f'{tag.name}.txt'),
                      'ephemeral': True if ephemeral is None else ephemeral}
        elif raw == 'Send Using Code Block':
            kwargs = {**self.maybe_codeblock(content=tag.content),
                      'ephemeral': True if ephemeral is None else ephemeral}
        else:
            kwargs = {'content': tag.content, 'embed': tag.embed,
                      'ephemeral': False if ephemeral is None else ephemeral}

        await interaction.response.send_message(**kwargs)

        try:
            query = "INSERT INTO commands (guild_id, user_id, command) VALUES ($1, $2, 'tag')"
            await tag.use(self.bot.pool)
            await self.bot.pool.execute(
                query,
                interaction.guild.id if interaction.guild else None,
                interaction.user.id)
        except Exception as e:
            await self.bot.exceptions.add_error(error=e)

    @slash_tag.autocomplete('tag_name')
    async def tag_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for the `/tag` command."""
        query = """
            WITH tags AS (
                SELECT name FROM tags 
                WHERE (guild_id = $1 OR guild_id IS NULL)
                AND ( CASE WHEN LENGTH($2) > 0 THEN ( SIMILARITY(name, $2) > (
                    CASE WHEN LENGTH($2) > 3 THEN 0.175 ELSE 0.05 END
                ) ) ELSE TRUE END )
                ORDER BY similarity(name, $2) LIMIT 50
            )
            SELECT DISTINCT name FROM tags ORDER BY name LIMIT 25
            
        """
        tags = await self.bot.pool.fetch(query, interaction.guild.id if interaction.guild else None, current)
        if tags:
            return [app_commands.Choice(name=f"{tag['name']}"[0:100], value=tag['name']) for tag in tags]
        ctx = await DuckContext.from_interaction(interaction)
        return [app_commands.Choice(name=await ctx.translate(40), value='list')]

async def setup(bot):
    await bot.add_cog(Tags(bot))
