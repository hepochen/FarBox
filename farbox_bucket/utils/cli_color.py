#coding: utf8
from __future__ import absolute_import, print_function

#CSI="\x1B["
#RED = CSI+"31;40m"
#GREEN = CSI+'32;40m'
#RESET =CSI+"m"


FLAGS = dict(
    RESET = "\x1B[0m",
    BOLD = "\x1B[1m",
    DIM = "\x1B[2m",
    UNDER = "\x1B[4m",
    REVERSE = "\x1B[7m",
    HIDE = "\x1B[8m",
    CLEARSCREEN = "\x1B[2J",
    CLEARLINE = "\x1B[2K",
    BLACK = "\x1B[30m",
    RED = "\x1B[31m",
    GREEN = "\x1B[32m",
    YELLOW = "\x1B[33m",
    BLUE = "\x1B[34m",
    MAGENTA = "\x1B[35m",
    CYAN = "\x1B[36m",
    WHITE = "\x1B[37m",
    BBLACK = "\x1B[40m",
    BRED = "\x1B[41m",
    BGREEN = "\x1B[42m",
    BYELLOW = "\x1B[43m",
    BBLUE = "\x1B[44m",
    BMAGENTA = "\x1B[45m",
    BCYAN = "\x1B[46m",
    BWHITE = "\x1B[47m",
    NEWLINE = "\r\n\x1B[0m",
)

def print_with_color(strings, color='red', end='\r\n'):
    color = FLAGS.get(color.upper())
    if color:
        print(color + strings + FLAGS['RESET'],  end=end)
    else:
        print(strings)


def print_colorful_parts(string_parts, end=''):
    for strings, color in string_parts:
        print_with_color(strings, color, end)
    print(FLAGS['NEWLINE'], end='')


if __name__ == '__main__':
    print_with_color('hello', 'green', end=' ')
    print_with_color('hello', 'blue')

    print_colorful_parts(
        [('hello', 'magenta'),
         ('world', 'yellow'),
         ('hello', 'red'),
         ('world', 'cyan')],
        end=' '
    )
