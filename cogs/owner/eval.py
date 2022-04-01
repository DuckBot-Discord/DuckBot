from __future__ import annotations

import contextlib
import io
import re
import textwrap
import traceback
import typing

import asyncio
import discord
from discord.ext import commands
from import_expression import exec as e_exec

from utils import DuckCog, DuckContext, DeleteButton
from bot import DuckBot

CODEBLOCK_REGEX = re.compile(r'`{3}(python\n|py\n|\n)?(?P<code>[^`]*)\n?`{3}')

class EvalCtxMenu(discord.ui.Modal):
    def __init__(self, last_code: str, *, timeout: int = 60*15, **kwargs):
        self.interaction: typing.Optional[discord.Interaction] = None
        self.body.default = last_code
        super().__init__(
            title='Evaluates Code',
        )

    body = discord.ui.TextInput(label='Code', placeholder='Enter code here', style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()

def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')

@discord.app_commands.context_menu(name='Evaluate Message')
async def eval_message(interaction: discord.Interaction, message: discord.Message):
    """ Evaluates the message content. """
    bot: DuckBot = interaction.client  # type: ignore

    if not await bot.is_owner(interaction.user):
        return await interaction.response.send_message(
            'You are not the owner of this bot!',
            ephemeral=True)

    if not message.content:
        return await interaction.response.send_message(
            'That message contained no content!',
            ephemeral=True)

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

    if isinstance(result, discord.File):
        await followup.send(file=result)
        await DeleteButton.to_destination(destination=followup, file=result, wait=True,
                                          author=interaction.user, delete_on_timeout=False)

    elif result and result.strip():
        await DeleteButton.to_destination(destination=followup, content=result, wait=True,
                                          author=interaction.user, delete_on_timeout=False)

    else:
        await interaction.edit_original_message(content='Done! Code ran with no output...',
                                                view=DeleteButton(message=None, author=interaction.user,
                                                                  delete_on_timeout=False))

class Eval(DuckCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_result = None
        self._last_context_menu_input = None

    # noinspection PyBroadException
    async def eval(self, body: str, env: typing.Dict[str, typing.Any]):
        """ Evaluates arbitrary python code """
        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        to_send: typing.Optional[str] = None

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            e_exec(to_compile, env)
        except Exception as e:
            to_send = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            if len(to_send) > 1990:
                return discord.File(io.BytesIO(to_send.encode('utf-8')), filename='eval_error.txt')
            return f"```py\n{to_send}\n```"

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            to_send = f'\n{value}{traceback.format_exc()}'
            if len(to_send) > 1990:
                return discord.File(io.BytesIO(to_send.encode('utf-8')), filename='output.py')
            return f"```py\n{to_send}```"

        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    to_send = f'{value}'
            else:
                self._last_result = ret
                to_send = f'{value}{ret}'
            if to_send:
                to_send = to_send.replace(self.bot.http.token, '[token omitted]')
                if len(to_send) > 1990:
                    return discord.File(io.BytesIO(to_send.encode('utf-8')), filename='output.py')
                else:
                    return f"```py\n{to_send}\n```"

    @commands.command(name='eval')
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
            await asyncio.sleep(1)
            try:
                await msg.add_reaction(
                    '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}')
            except discord.HTTPException:
                pass

        async def cancel_task(t: asyncio.Task):
            t.cancel()

        task = self.bot.create_task(react_with_play(ctx.message))
        result = await self.eval(body, env)
        self.bot.create_task(cancel_task(task))

        if isinstance(result, discord.File):
            await DeleteButton.to_destination(destination=ctx, file=result, author=ctx.author, delete_on_timeout=False)

        elif result and result.strip():
            await DeleteButton.to_destination(destination=ctx, content=result, author=ctx.author, delete_on_timeout=False)

        else:
            try:
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            except discord.HTTPException:
                pass

    async def cog_load(self) -> None:
        self.bot.tree.add_command(eval_message)
        self.bot._eval_cog = self

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            eval_message.name, type=discord.AppCommandType.message
        )
        try:
            del self.bot._eval_cog  # noqa
        except AttributeError:
            pass

    @discord.app_commands.command(name='eval')
    @discord.app_commands.describe(body='The body to evaluate')
    async def slash_eval(self, interaction: discord.Interaction, body: str = None):
        """Evaluates arbitrary python code"""

        bot: DuckBot = interaction.client  # type: ignore

        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message(
                'You are not the owner of this bot!',
                ephemeral=True)

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

        if isinstance(result, discord.File):
            await DeleteButton.to_destination(destination=followup, file=result, wait=True,
                                              author=interaction.user, delete_on_timeout=False)

        elif result and result.strip():
            await DeleteButton.to_destination(destination=followup, content=result, wait=True,
                                              author=interaction.user, delete_on_timeout=False)

        else:
            if timed_out is None:
                await followup.send(content='Done! Code ran with no output...', ephemeral=True,
                                    view=DeleteButton(author=interaction.user, delete_on_timeout=False))
            else:
                await followup.send(content='Done! Code ran with no output...', ephemeral=True)
