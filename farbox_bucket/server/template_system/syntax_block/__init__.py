# coding: utf8
from .pure import pure
from .lazy_html import tab
from .refer import refer
from .compatibility import syntax_block_compatibility
from .page import page

syntax_blocks = {
    'pure': pure,
    'tab': tab,
    "refer": refer,
    "page": page,

    # compatibility for Bitcron
    "footer": syntax_block_compatibility,
    "browser": syntax_block_compatibility,
    "font": syntax_block_compatibility,
}