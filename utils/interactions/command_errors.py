import contextlib
import traceback

import discord
from bot import DuckBot
from discord import app_commands
from discord.ext.commands import UserInputError
from typing import Union, Optional
from utils.bases.errors import SilentCommandError, DuckBotException
from . import errors
import logging


async def on_app_command_error(
        interaction: discord.Interaction,
        command: Optional[Union[app_commands.ContextMenu, app_commands.Command]],
        error: app_commands.AppCommandError,
) -> None:
    response: discord.InteractionResponse = interaction.response  # type: ignore
    bot: DuckBot = interaction.client  # type: ignore

    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original

    if isinstance(error, app_commands.CommandNotFound):
        if not response._responded:  # noqa
            await response.send_message('**Sorry, but somehow this application command does not exist anymore.**'
                                        '\nIf you think this command should exist, please ask about it in our '
                                        '[support server](https://discord.gg/TdRfGKg8Wh)!'
                                        ' Application commands are still a work in progress '
                                        'and we are working hard to make them better.', ephemeral=True)
    elif isinstance(error, SilentCommandError):
        logging.debug(f'Ignoring silent command error raised in application command {command}', exc_info=False)
        return
    elif isinstance(error, (DuckBotException, UserInputError, errors.InteractionError)):
        if not response._responded:  # noqa
            await response.send_message(str(error), ephemeral=True)
        else:
            webhook: discord.Webhook = interaction.followup  # noqa
            with contextlib.suppress(discord.HTTPException):
                await webhook.send(content=str(error), ephemeral=True)
    elif isinstance(error, app_commands.CommandSignatureMismatch):
        if not response._responded:  # noqa
            await bot.exceptions.add_error(error=error)
            try:
                await response.send_message(f"**\N{WARNING SIGN} This command's signature is out of date!**\n"
                                            f"i've warned the developers about this and it will "
                                            f"be fixed as soon as possible", ephemeral=True)
            except discord.HTTPException:
                pass

        else:
            webhook: discord.Webhook = interaction.followup  # noqa
            try:
                await webhook.send(content=f"**\N{WARNING SIGN} This command's signature is out of date!**\n"
                                           f"i've warned the developers about this and it will "
                                           f"be fixed as soon as possible", ephemeral=True)
            except discord.HTTPException:
                pass

    else:
        await bot.exceptions.add_error(error=error)

        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        embed = discord.Embed(title='Error traceback:', description=f'```py\n{tb[0:4080]}\n```',
                              color=discord.Color.red())
        embed.set_footer(text='This error has bee succesfully reported to the developers.',
                         icon_url='https://cdn.discordapp.com/emojis/912190496791728148.gif?size=60&quality=lossless')
        msg = '**Sorry, but something went wrong while executing this application command.**\n' \
              '__You can also join our [support server](https://discord.gg/TdRfGKg8Wh) if you' \
              ' want help with this error!__\n_ _'

        if not response._responded:
            await response.send_message(msg, ephemeral=True, embed=embed)
        else:

            await interaction.followup.send(msg, embed=embed, ephemeral=True)


async def setup(bot: DuckBot) -> None:
    bot.add_listener(on_app_command_error)
