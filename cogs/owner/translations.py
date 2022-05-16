from typing import Optional, List, Any

from discord.ext import commands

from utils import command, DuckCog, DuckContext


class LocaleFlags(commands.FlagConverter, case_insensitive=True, prefix='--', delimiter=' '):
    english: str | None = commands.Flag(name='english', aliases=['en'])  # type: ignore
    spanish: str | None = commands.Flag(name='spanish', aliases=['es'])  # type: ignore
    italian: str | None = commands.Flag(name='italian', aliases=['it'], default=None)  # type: ignore


class TranslationManager(DuckCog):

    # noinspection SqlInsertValues
    @command()
    async def translate(self, ctx: DuckContext, translation_id: Optional[int] = None, *, flags: LocaleFlags) -> None:
        """|coro|
        Translates a translation ID.
        """
        if not flags.english and not flags.italian and not flags.spanish:
            await ctx.send('No translation flags were specified.')
            return

        query = "INSERT INTO translations ("
        if translation_id is not None:
            query_args: List[str] = ['tr_id']
            args: List[Any] = [translation_id]
        else:
            query_args = []
            args = []

        if flags.english:
            query_args.append('en_us')
            args.append(flags.english)

        if flags.italian:
            query_args.append('it')
            args.append(flags.italian)

        if flags.spanish:
            query_args.append('es_es')
            args.append(flags.spanish)

        query += ', '.join(query_args) + ') VALUES (' + ', '.join(f'${x+1}' for x in range(len(query_args))) + ')'

        if translation_id is not None:
            query += ' ON CONFLICT (tr_id) DO UPDATE SET ' + ', '.join(
                f'{x} = ${i}' for i, x in enumerate(query_args[1:], start=2)
            )

        query += ' RETURNING tr_id;'

        _id = await self.bot.pool.fetchval(query, *args)
        await ctx.send(
            f'Updated translation of ID {_id} for languages '
            f'{", ".join(query_args[(1 if translation_id is not None else 0):])}.'
        )
