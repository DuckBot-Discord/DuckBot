from __future__ import annotations
import asyncio

import datetime
from typing import Any, List, Optional, Union, Tuple, TYPE_CHECKING

from discord import Embed, Locale
from discord.types.embed import EmbedType
from discord.embeds import EmbedProxy
from discord import Colour

if TYPE_CHECKING:
    from typing_extensions import Self
    from bot import DuckBot
    from discord.embeds import (
        _EmbedAuthorProxy,
        _EmbedFieldProxy,
        _EmbedFooterProxy,
        _EmbedMediaProxy,
    )


__all__: Tuple[str, ...] = (
    "TranslatedEmbed",
    "FormatString",
)


class EmbedStore:
    """
    Helper to store translated embeds.
    """

    __slots__: Tuple[str, ...] = ("en_us", "es_es", "it")

    def __init__(self) -> None:
        self.en_us: Embed | None = None
        self.es_es: Embed | None = None
        self.it: Embed | None = None

    def get(self, locale: str) -> Embed | None:
        locale = locale.lower().replace("-", "_")
        if locale not in self.__slots__:
            raise ValueError(f"Locale {locale} not valid")
        return getattr(self, locale, None)

    def __setitem__(self, __name: str, __value: Any) -> None:
        if __name not in self.__slots__:
            raise ValueError(f"Locale {__name} not valid")
        super().__setattr__(__name, __value)


class FormatString:
    __slots__: Tuple[str, ...] = ("id", "args")

    def __init__(self, id: int, *args: Any) -> None:
        self.id: int = id
        self.args: Tuple[Any, ...] = args


class TranslatedEmbed:
    __slots__: Tuple[str, ...] = Embed.__slots__ + ("store", "tr_lock")

    def __init__(
        self,
        *,
        colour: Optional[Union[int, Colour]] = None,
        color: Optional[Union[int, Colour]] = None,
        title: Optional[Any] = None,
        type: EmbedType = "rich",
        url: Optional[Any] = None,
        description: Optional[Any] = None,
        timestamp: Optional[datetime.datetime] = None,
    ):
        self.colour = colour if colour is not None else color
        self.title: Optional[str | int | FormatString] = title
        self.type: EmbedType = type
        self.url: Optional[str | int | FormatString] = url
        self.description: Optional[str | int | FormatString] = description

        if timestamp is not None:
            self.timestamp = timestamp

        self.store = EmbedStore()
        self.tr_lock = asyncio.Lock()

    @property
    def colour(self) -> Optional[Colour]:
        return getattr(self, "_colour", None)

    @colour.setter
    def colour(self, value: Optional[Union[int, Colour]]) -> None:
        if value is None:
            self._colour = None
        elif isinstance(value, Colour):
            self._colour = value
        elif isinstance(value, int):
            self._colour = Colour(value=value)
        else:
            raise TypeError(f"Expected discord.Colour, int, or None but received {value.__class__.__name__} instead.")

    color = colour

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        return getattr(self, "_timestamp", None)

    @timestamp.setter
    def timestamp(self, value: Optional[datetime.datetime]) -> None:
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.astimezone()
            self._timestamp = value
        elif value is None:
            self._timestamp = None
        else:
            raise TypeError(f"Expected datetime.datetime or None received {value.__class__.__name__} instead")

    @property
    def footer(self) -> _EmbedFooterProxy:
        """Returns an ``EmbedProxy`` denoting the footer contents.

        See :meth:`set_footer` for possible values you can access.

        If the attribute has no value then ``None`` is returned.
        """
        # Lying to the type checker for better developer UX.
        return EmbedProxy(getattr(self, "_footer", {}))  # type: ignore

    def set_footer(self, *, text: Optional[Any] = None, icon_url: Optional[Any] = None) -> Self:
        """Sets the footer for the embed content.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        -----------
        text: :class:`str`
            The footer text. Can only be up to 2048 characters.
        icon_url: :class:`str`
            The URL of the footer icon. Only HTTP(S) is supported.
        """

        self._footer = {}
        if text is not None:
            self._footer["text"] = text

        if icon_url is not None:
            self._footer["icon_url"] = icon_url

        return self

    def remove_footer(self) -> Self:
        """Clears embed's footer information.

        This function returns the class instance to allow for fluent-style
        chaining.

        .. versionadded:: 2.0
        """
        try:
            del self._footer
        except AttributeError:
            pass

        return self

    @property
    def image(self) -> _EmbedMediaProxy:
        """Returns an ``EmbedProxy`` denoting the image contents.

        Possible attributes you can access are:

        - ``url``
        - ``proxy_url``
        - ``width``
        - ``height``

        If the attribute has no value then ``None`` is returned.
        """
        # Lying to the type checker for better developer UX.
        return EmbedProxy(getattr(self, "_image", {}))  # type: ignore

    def set_image(self, *, url: Optional[Any]) -> Self:
        """Sets the image for the embed content.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        -----------
        url: :class:`str`
            The source URL for the image. Only HTTP(S) is supported.
        """

        if url is None:
            try:
                del self._image
            except AttributeError:
                pass
        else:
            self._image = {
                "url": url,
            }

        return self

    @property
    def thumbnail(self) -> _EmbedMediaProxy:
        """Returns an ``EmbedProxy`` denoting the thumbnail contents.

        Possible attributes you can access are:

        - ``url``
        - ``proxy_url``
        - ``width``
        - ``height``

        If the attribute has no value then ``None`` is returned.
        """
        # Lying to the type checker for better developer UX.
        return EmbedProxy(getattr(self, "_thumbnail", {}))  # type: ignore

    def set_thumbnail(self, *, url: Optional[Any]) -> Self:
        """Sets the thumbnail for the embed content.

        This function returns the class instance to allow for fluent-style
        chaining.

        .. versionchanged:: 1.4
            Passing ``None`` removes the thumbnail.

        Parameters
        -----------
        url: :class:`str`
            The source URL for the thumbnail. Only HTTP(S) is supported.
        """

        if url is None:
            try:
                del self._thumbnail
            except AttributeError:
                pass
        else:
            self._thumbnail = {
                "url": url,
            }

        return self

    @property
    def author(self) -> _EmbedAuthorProxy:
        """Returns an ``EmbedProxy`` denoting the author contents.

        See :meth:`set_author` for possible values you can access.

        If the attribute has no value then ``None`` is returned.
        """
        # Lying to the type checker for better developer UX.
        return EmbedProxy(getattr(self, "_author", {}))  # type: ignore

    def set_author(self, *, name: Any, url: Optional[Any] = None, icon_url: Optional[Any] = None) -> Self:
        """Sets the author for the embed content.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        -----------
        name: :class:`str`
            The name of the author. Can only be up to 256 characters.
        url: :class:`str`
            The URL for the author.
        icon_url: :class:`str`
            The URL of the author icon. Only HTTP(S) is supported.
        """

        self._author = {
            "name": name,
        }

        if url is not None:
            self._author["url"] = url

        if icon_url is not None:
            self._author["icon_url"] = icon_url

        return self

    def remove_author(self) -> Self:
        """Clears embed's author information.

        This function returns the class instance to allow for fluent-style
        chaining.

        .. versionadded:: 1.4
        """
        try:
            del self._author
        except AttributeError:
            pass

        return self

    @property
    def fields(self) -> List[_EmbedFieldProxy]:
        """List[``EmbedProxy``]: Returns a :class:`list` of ``EmbedProxy`` denoting the field contents.

        See :meth:`add_field` for possible values you can access.

        If the attribute has no value then ``None`` is returned.
        """
        # Lying to the type checker for better developer UX.
        return [EmbedProxy(d) for d in getattr(self, "_fields", [])]  # type: ignore

    def add_field(self, *, name: Any, value: Any, inline: bool = True) -> Self:
        """Adds a field to the embed object.

        This function returns the class instance to allow for fluent-style
        chaining. Can only be up to 25 fields.

        Parameters
        -----------
        name: :class:`str`
            The name of the field. Can only be up to 256 characters.
        value: :class:`str`
            The value of the field. Can only be up to 1024 characters.
        inline: :class:`bool`
            Whether the field should be displayed inline.
        """

        field = {
            "inline": inline,
            "name": name,
            "value": value,
        }

        try:
            self._fields.append(field)
        except AttributeError:
            self._fields = [field]

        return self

    def insert_field_at(self, index: int, *, name: Any, value: Any, inline: bool = True) -> Self:
        """Inserts a field before a specified index to the embed.

        This function returns the class instance to allow for fluent-style
        chaining. Can only be up to 25 fields.

        .. versionadded:: 1.2

        Parameters
        -----------
        index: :class:`int`
            The index of where to insert the field.
        name: :class:`str`
            The name of the field. Can only be up to 256 characters.
        value: :class:`str`
            The value of the field. Can only be up to 1024 characters.
        inline: :class:`bool`
            Whether the field should be displayed inline.
        """

        field = {
            "inline": inline,
            "name": name,
            "value": value,
        }

        try:
            self._fields.insert(index, field)
        except AttributeError:
            self._fields = [field]

        return self

    def clear_fields(self) -> None:
        """Removes all fields from this embed."""
        try:
            self._fields.clear()
        except AttributeError:
            self._fields = []

    def remove_field(self, index: int) -> None:
        """Removes a field at a specified index.

        If the index is invalid or out of bounds then the error is
        silently swallowed.

        .. note::

            When deleting a field by index, the index of the other fields
            shift to fill the gap just like a regular list.

        Parameters
        -----------
        index: :class:`int`
            The index of the field to remove.
        """
        try:
            del self._fields[index]
        except (AttributeError, IndexError):
            pass

    def set_field_at(self, index: int, *, name: Any, value: Any, inline: bool = True) -> Self:
        """Modifies a field to the embed object.

        The index must point to a valid pre-existing field. Can only be up to 25 fields.

        This function returns the class instance to allow for fluent-style
        chaining.

        Parameters
        -----------
        index: :class:`int`
            The index of the field to modify.
        name: :class:`str`
            The name of the field. Can only be up to 256 characters.
        value: :class:`str`
            The value of the field. Can only be up to 1024 characters.
        inline: :class:`bool`
            Whether the field should be displayed inline.

        Raises
        -------
        IndexError
            An invalid index was provided.
        """

        try:
            field = self._fields[index]
        except (TypeError, IndexError, AttributeError):
            raise IndexError("field index out of range")

        field["name"] = name
        field["value"] = value
        field["inline"] = inline
        return self

    async def translate(self, bot: DuckBot, locale: str | Locale) -> Embed:
        """|coro|
        Translates the embed into the given language.

        This function is called automatically if the embed is sent to a
        :class:`utils.DuckContext.send`.

        Parameters
        -----------
        bot: :class:`bot.DuckBot`
            The bot instance.
        locale: Union[:class:`str`, :class:`~discord.Locale`]
        """

        locale = bot.validate_locale(locale)

        e = self.store.get(locale)
        if e is not None:
            return e

        async with bot.pool.acquire() as conn:
            embed = Embed(color=self.color, timestamp=self.timestamp)

            if isinstance(self.title, int):
                embed.title = await bot.translate(self.title, locale=locale, db=conn)
            elif isinstance(self.title, FormatString):
                embed.title = await bot.translate(self.title.id, *self.title.args, locale=locale, db=conn)
            else:
                embed.title = self.title

            if isinstance(self.description, int):
                embed.description = await bot.translate(self.description, locale=locale, db=conn)
            elif isinstance(self.description, FormatString):
                embed.description = await bot.translate(self.description.id, *self.description.args, locale=locale, db=conn)
            else:
                embed.description = self.description

            if self.footer:
                kwargs = {}
                if isinstance(self.footer.text, int):
                    kwargs["text"] = await bot.translate(self.footer.text, locale=locale, db=conn)
                elif isinstance(self.footer.text, FormatString):
                    kwargs["text"] = await bot.translate(
                        self.footer.text.id,
                        *self.footer.text.args,
                        locale=locale,
                        db=conn,
                    )
                else:
                    kwargs["text"] = self.footer.text

                if isinstance(self.footer.icon_url, int):
                    kwargs["icon_url"] = await bot.translate(self.footer.icon_url, locale=locale, db=conn)
                elif isinstance(self.footer.icon_url, FormatString):
                    kwargs["icon_url"] = await bot.translate(
                        self.footer.icon_url.id,
                        *self.footer.icon_url.args,
                        locale=locale,
                        db=conn,
                    )
                else:
                    kwargs["icon_url"] = self.footer.icon_url

                embed.set_footer(**kwargs)

            if isinstance(self.image.url, int):
                embed.set_image(url=await bot.translate(self.image.url, locale=locale, db=conn))
            elif isinstance(self.image.url, FormatString):
                embed.set_image(url=await bot.translate(self.image.url.id, *self.image.url.args, locale=locale, db=conn))
            else:
                embed.set_image(url=self.image.url)

            if isinstance(self.thumbnail.url, int):
                embed.set_thumbnail(url=await bot.translate(self.thumbnail.url, locale=locale, db=conn))
            elif isinstance(self.thumbnail.url, FormatString):
                embed.set_thumbnail(
                    url=await bot.translate(
                        self.thumbnail.url.id,
                        *self.thumbnail.url.args,
                        locale=locale,
                        db=conn,
                    )
                )
            else:
                embed.set_thumbnail(url=self.thumbnail.url)

            if self.author:
                kwargs = {}
                if isinstance(self.author.name, int):
                    kwargs["name"] = await bot.translate(self.author.name, locale=locale, db=conn)
                elif isinstance(self.author.name, FormatString):
                    kwargs["name"] = await bot.translate(
                        self.author.name.id,
                        *self.author.name.args,
                        locale=locale,
                        db=conn,
                    )
                else:
                    kwargs["name"] = self.author.name

                if isinstance(self.author.url, int):
                    kwargs["url"] = await bot.translate(self.author.url, locale=locale, db=conn)
                elif isinstance(self.author.url, FormatString):
                    kwargs["url"] = await bot.translate(
                        self.author.url.id,
                        *self.author.url.args,
                        locale=locale,
                        db=conn,
                    )
                else:
                    kwargs["url"] = self.author.url

                if isinstance(self.author.icon_url, int):
                    kwargs["icon_url"] = await bot.translate(self.author.icon_url, locale=locale, db=conn)
                elif isinstance(self.author.icon_url, FormatString):
                    kwargs["icon_url"] = await bot.translate(
                        self.author.icon_url.id,
                        *self.author.icon_url.args,
                        locale=locale,
                        db=conn,
                    )
                else:
                    kwargs["icon_url"] = self.author.icon_url

                embed.set_author(**kwargs)

            for field in self.fields:
                kwargs = {}
                if isinstance(field.name, int):
                    kwargs["name"] = await bot.translate(field.name, locale=locale, db=conn)
                elif isinstance(field.name, FormatString):
                    kwargs["name"] = await bot.translate(field.name.id, *field.name.args, locale=locale, db=conn)
                else:
                    kwargs["name"] = field.name

                if isinstance(field.value, int):
                    kwargs["value"] = await bot.translate(field.value, locale=locale, db=conn)
                elif isinstance(field.value, FormatString):
                    kwargs["value"] = await bot.translate(field.value.id, *field.value.args, locale=locale, db=conn)
                else:
                    kwargs["value"] = field.value

                kwargs["inline"] = field.inline

                embed.add_field(**kwargs)

            self.store[locale] = embed

        return embed
