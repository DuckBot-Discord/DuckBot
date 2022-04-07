import copy
import textwrap
from typing import Tuple

BOT_ANSI_ART = """██████╗ ██╗   ██╗ ██████╗██╗  ██╗██████╗  ██████╗ ████████╗
██╔══██╗██║   ██║██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝
██║  ██║██║   ██║██║     █████╔╝ ██████╔╝██║   ██║   ██║   
██║  ██║██║   ██║██║     ██╔═██╗ ██╔══██╗██║   ██║   ██║   
██████╔╝╚██████╔╝╚██████╗██║  ██╗██████╔╝╚██████╔╝   ██║   
╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   """

def text_color(text: str, color: Tuple[int, int, int]):
    return "\033[38;2;{};{};{}m{}\033[0m".format(*color, text)


def duck_fade(text):
    _new_text = ""
    _min = (244, 213, 140)
    _max = (256, 256, 256)
    _range = (_max[0] - _min[0],
              _max[1] - _min[1],
              _max[2] - _min[2])
    for line in text.splitlines():
        _step = (_range[0] // len(line),
                 _range[1] // len(line),
                 _range[2] // len(line))
        _current = copy.copy(_min)
        for c in line:
            _current = (_current[0] + _step[0],
                        _current[1] + _step[1],
                        _current[2] + _step[2])
            if any(i >= 256 for i in _current):
                _current = copy.copy(_min)
            _new_text += text_color(c, _current)
        _new_text += "\n"
    return _new_text


if __name__ == '__main__':
    print(textwrap.indent(duck_fade(BOT_ANSI_ART), "    "))
