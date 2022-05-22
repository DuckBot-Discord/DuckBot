import asyncio
import click
import logging

from utils import col
from utils.bases.launcher import run_bot


@click.command()
@click.option('--dump', default=None, help='Dump translations to file.')
@click.option('--load', default=None, help='Load translations from file.')
@click.option('--norun', is_flag=True, help='Add to not run the bot.')
@click.option('--brief', is_flag=True, help='Brief logging output.')
def run(dump, norun, load, brief):
    """Options to run the bot."""

    if brief:
        fmt = f'[{col(4)}%(name)s{col()}] %(message)s{col()}'
    else:
        fmt = (
            f'{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s{col()}'
        )

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
    )

    asyncio.run(run_bot(to_dump=dump, to_load=load, run=(not norun if (not dump or not load) else False)))


if __name__ == '__main__':
    run()
