#coding: utf8
from __future__ import absolute_import
import sys, getopt



# getopt.getopt(['--file=error.txt', '-h', '-v', '6',  '--version', '9'], 'hv:', ['file=', 'version'])
#getopt.getopt([ 'farbox', '--file=error.txt', '--version','-h', '-v', '6'], 'hv:', ['file=', 'version'])
# getopt.getopt(['--file=error.txt', '--version','-h', '-v', '6', '9'], 'hv:', ['file=', 'version'])
# ([('--file', 'error.txt'), ('-h', ''), ('-v', '6'), ('--version', '')], ['9'])

def get_args_from_console(raw_args=None, short_opts='', long_opts=None):
    if raw_args is None:
        raw_args = sys.argv[1:]
    long_opts = long_opts or []
    opts, args = getopt.getopt(raw_args, short_opts, long_opts)
    kwargs = {}
    for k, v in opts:
        k = k.strip('-')
        kwargs[k] = v
    return kwargs, args


def get_first_arg_from_console():
    raw_args = sys.argv[1:]
    if raw_args:
        return raw_args[0]
    else:
        return None