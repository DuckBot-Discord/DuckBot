from __future__ import annotations

import contextlib
import io
import pprint
import random
import re

import aiohttp
import textwrap
import traceback
import typing

import asyncio
import discord
from discord.ext import commands
from import_expression import exec as e_exec

from utils import DuckCog, DuckContext, DeleteButton, command, TranslatedEmbed
from bot import DuckBot

CODEBLOCK_REGEX = re.compile(r'`{3}(python\n|py\n|\n)?(?P<code>[^`]*)\n?`{3}')


class TextInput(discord.ui.TextInput):
    if typing.TYPE_CHECKING:
        value: str


class EvalCtxMenu(discord.ui.Modal):
    def __init__(self, last_code: typing.Optional[str], *, timeout: int = 60 * 15, **kwargs):
        self.interaction: typing.Optional[discord.Interaction] = None
        self.body.default = last_code
        super().__init__(
            title='Evaluates Code',
        )

    body = TextInput(label='Code', placeholder='Enter code here', style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()


def cleanup_code(content: str):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


@discord.app_commands.context_menu(name='Evaluate Message')
async def eval_message(interaction: discord.Interaction, message: discord.Message):
    """Evaluates the message content."""
    bot: DuckBot = interaction.client  # type: ignore

    if not await bot.is_owner(interaction.user):
        return await interaction.response.send_message('You are not the owner of this bot!', ephemeral=True)

    if not message.content:
        return await interaction.response.send_message('That message contained no content!', ephemeral=True)

    await interaction.response.defer()

    body = message.content

    # Handling jishaku code
    command_names: tuple = ('jishaku py ', 'jishaku python ', 'jsk py ', 'jsk python ')
    if any(x in body for x in command_names):
        body = re.split('|'.join(command_names), body, maxsplit=1)[-1]
    else:
        # Handling code blocks
        found = CODEBLOCK_REGEX.search(body)
        if found:
            body = found.group('code')

    followup: discord.Webhook = interaction.followup  # type: ignore
    eval_cog: Eval = bot._eval_cog  # noqa

    env = {
        'bot': bot,
        'ctx': await bot.get_context(message),
        'interaction': interaction,
        'channel': interaction.channel,
        '_c': interaction.channel,
        'author': interaction.user,
        '_a': interaction.user,
        'guild': interaction.guild,
        '_g': interaction.guild,
        'message': message,
        '_m': message,
        '_': eval_cog._last_result,  # noqa
        '_r': getattr(message.reference, 'resolved', None),
        '_get': discord.utils.get,
        '_find': discord.utils.find,
        '_now': discord.utils.utcnow,
    }

    result = await eval_cog.eval(body, env)

    if result:
        await DeleteButton.to_destination(
            **result, destination=followup, wait=True, author=interaction.user, delete_on_timeout=False
        )
    else:
        await DeleteButton.to_destination(
            content='Done! Code ran with no output...',
            destination=followup,
            author=interaction.user,
            delete_on_timeout=False,
            wait=True,
        )


class Eval(DuckCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_result = None
        self._last_context_menu_input = None

    async def cog_load(self) -> None:
        self.bot.tree.add_command(eval_message)
        self.bot._eval_cog = self

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(eval_message.name, type=discord.AppCommandType.message)
        try:
            del self.bot._eval_cog
        except AttributeError:
            pass

    @staticmethod
    def handle_return(ret: typing.Any, stdout: str | None = None) -> dict | None:
        kwargs = {}
        if isinstance(ret, discord.File):
            kwargs['files'] = [ret]
        elif isinstance(ret, (discord.Embed, TranslatedEmbed)):
            kwargs['embeds'] = ret
        elif isinstance(ret, discord.Message):
            kwargs['content'] = f"{repr(ret)}"
        elif isinstance(ret, Exception):
            kwargs['content'] = "".join(traceback.format_exception(type(ret), ret, ret.__traceback__))
        elif ret is None:
            pass
        else:
            kwargs['content'] = f"{ret}"

        if stdout:
            kwargs['content'] = f"{kwargs.get('content', '')}{stdout}"

        if (content := kwargs.get('content')) and len(content) > 1990:
            files = kwargs.get('files', [])
            file = discord.File(io.BytesIO(content.encode()), filename='output.py')
            files.append(file)
            kwargs['files'] = files
        elif content:
            kwargs['content'] = f"```py\n{content}\n```"

        return kwargs or None

    @staticmethod
    def clean_globals():
        return {
            '__name__': __name__,
            '__package__': __package__,
            '__file__': __file__,
            '__builtins__': __builtins__,
            'annotations': annotations,
            'traceback': traceback,
            'io': io,
            'typing': typing,
            'asyncio': asyncio,
            'discord': discord,
            'datetime': commands,
            'aiohttp': aiohttp,
            're': re,
            'random': random,
            'pprint': pprint,
        }

    # noinspection PyBroadException
    async def eval(self, body: str, env: typing.Dict[str, typing.Any]) -> dict | None:
        """Evaluates arbitrary python code"""
        env.update(self.clean_globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        to_send: typing.Optional[str] = None

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            e_exec(to_compile, env)
        except Exception as e:
            return self.handle_return(e)

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            return self.handle_return(to_send, stdout=value)

        else:
            value = stdout.getvalue()
            if ret is not None:
                self._last_result = ret
            return self.handle_return(ret, stdout=value)

    @command(name='eval')
    async def eval_command(self, ctx: DuckContext, *, body: str):
        """Evaluates arbitrary python code"""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            '_c': ctx.channel,
            'author': ctx.author,
            '_a': ctx.author,
            'guild': ctx.guild,
            '_g': ctx.guild,
            'message': ctx.message,
            '_m': ctx.message,
            '_': self._last_result,
            '_r': getattr(ctx.message.reference, 'resolved', None),
            '_get': discord.utils.get,
            '_find': discord.utils.find,
            '_now': discord.utils.utcnow,
        }

        async def react_with_play(msg: discord.Message):
            await asyncio.sleep(1.5)
            try:
                await msg.add_reaction('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}')
            except discord.HTTPException:
                pass

        task = self.bot.create_task(react_with_play(ctx.message))
        result = await self.eval(body, env)
        task.cancel()

        if result:
            await DeleteButton.to_destination(**result, destination=ctx, author=ctx.author, delete_on_timeout=False)

        else:
            try:
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            except discord.HTTPException:
                pass

    @discord.app_commands.command(name='eval')
    @discord.app_commands.describe(body='The body to evaluate')
    async def slash_eval(self, interaction: discord.Interaction, body: typing.Optional[str]):
        """Evaluates arbitrary python code"""

        bot: DuckBot = interaction.client  # type: ignore

        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message('You are not the owner of this bot!', ephemeral=True)

        timed_out = None

        if body is None:
            ctx_menu = EvalCtxMenu(last_code=self._last_context_menu_input)
            await interaction.response.send_modal(ctx_menu)
            timed_out = await ctx_menu.wait()
            if timed_out:
                return
            body = ctx_menu.body.value
            self._last_context_menu_input = body
            interaction = ctx_menu.interaction or interaction
        else:
            await interaction.response.defer()

        followup: discord.Webhook = interaction.followup  # type: ignore

        env = {
            'bot': bot,
            'ctx': None,
            'interaction': interaction,
            'channel': interaction.channel,
            '_c': interaction.channel,
            'author': interaction.user,
            '_a': interaction.user,
            'guild': interaction.guild,
            '_g': interaction.guild,
            'message': None,
            '_m': None,
            '_': self._last_result,
            '_r': None,
            '_get': discord.utils.get,
            '_find': discord.utils.find,
            '_now': discord.utils.utcnow,
        }

        result = await self.eval(body, env)

        if result:
            await DeleteButton.to_destination(
                **result, destination=followup, wait=True, author=interaction.user, delete_on_timeout=False
            )
        else:
            if timed_out is None:
                await DeleteButton.to_destination(
                    content='Done! Code ran with no output...',
                    destination=followup,
                    author=interaction.user,
                    delete_on_timeout=False,
                    wait=True,
                )
            else:
                await followup.send(content='Done! Code ran with no output...', ephemeral=True)
