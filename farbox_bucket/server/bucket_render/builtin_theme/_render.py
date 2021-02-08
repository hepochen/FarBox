# coding: utf8

from .wiki import show_wiki_as_sub_site, show_wiki_nodes_as_sub_site
from .album import show_albums_as_sub_site


sub_site_funcs = [
    show_albums_as_sub_site,
    show_wiki_as_sub_site,
    show_wiki_nodes_as_sub_site,
]

def show_builtin_theme_as_sub_site():
    for sub_site_func in sub_site_funcs:
        sub_site_html = sub_site_func()
        if sub_site_html:
            return sub_site_html
