import logging
from . import col
from typing import Tuple

__all__: Tuple[str, ...] = ('ColourFormatter',)


class ColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40m', f'|{col(4)}%(name)s'),
        (logging.INFO, '\x1b[32m', f'|{col(4)}%(name)s'),
        (logging.WARNING, '\x1b[33;1m', f'|{col(4)}%(name)s.%(funcName)s:%(lineno)s{col()}'),
        (logging.ERROR, '\x1b[31;1;4m', f'|{col(4)}%(name)s.%(funcName)s:%(lineno)s{col()}'),
        (logging.CRITICAL, '\x1b[41;1;4m', f'|{col(4)}%(name)s.%(funcName)s:%(lineno)s{col()}'),
    ]

    def __init__(self, brief: bool) -> None:
        super().__init__()

        '\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s'

        if brief:
            fmt = f'[{col(4)}%(name)s{col()}] %(message)s{col()}'
        else:
            fmt = f'{col()}[{col(7)}%(asctime)s{col()}|{{colour}}%(levelname)s{col()}{{extra}}] %(message)s{col()}'

        self.FORMATS = {
            level: logging.Formatter(
                fmt.format(colour=colour, extra=extra),
            )
            for level, colour, extra in self.LEVEL_COLOURS
        }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output
