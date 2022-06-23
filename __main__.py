import asyncio
import click
import logging

from utils.bases.launcher import run_bot
from utils import ColourFormatter


@click.command()
@click.option('--dump', default=None, help='Dump translations to file.')
@click.option('--load', default=None, help='Load translations from file.')
@click.option('--norun', is_flag=True, help='Add to not run the bot.')
@click.option('--brief', is_flag=True, help='Brief logging output.')
def run(dump, norun, load, brief):
    """Options to run the bot."""

    handler = logging.StreamHandler()
    handler.setFormatter(ColourFormatter(brief=brief))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )

    asyncio.run(run_bot(to_dump=dump, to_load=load, run=(not norun if (not dump or not load) else False)))


if __name__ == '__main__':
    run()
