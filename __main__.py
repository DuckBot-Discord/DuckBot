import asyncio
import click
import logging

from utils.bases.launcher import run_bot
from utils import ColourFormatter


@click.command()
@click.option('--brief', is_flag=True, help='Brief logging output.')
def run(brief):
    """Options to run the bot."""

    handler = logging.StreamHandler()
    handler.setFormatter(ColourFormatter(brief=brief))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )

    asyncio.run(run_bot())


if __name__ == '__main__':
    run()
