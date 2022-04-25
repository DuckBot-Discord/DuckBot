import asyncio
import click

from utils.launcher import run_bot


@click.command()
@click.option('--dump', default=None, help='Dump translations to file.')
@click.option('--load', default=None, help='Load translations from file.')
@click.option('--norun', is_flag=True, help='Add to not run the bot.')
def run(dump, norun, load):
    """Options to run the bot."""
    asyncio.run(run_bot(to_dump=dump, to_load=load,
    run=(not norun if (not dump or not load) else False)))
    

if __name__ == '__main__':
    run()