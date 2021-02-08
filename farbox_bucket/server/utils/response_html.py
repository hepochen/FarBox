# coding: utf8
import re
from farbox_bucket.utils import get_value_from_data, str_type, unicode_type, string_types, to_bytes, to_unicode
from farbox_bucket.server.utils.request_context_vars import get_no_html_inject_in_request


def insert_into_footer(to_insert, html, force=False):
    # 插入到 html 页面的尾部
    if not force and get_no_html_inject_in_request():
        return html
    if not to_insert:
        return html
    if isinstance(html, str_type) and isinstance(to_insert, unicode_type):
        to_insert = to_bytes(to_insert)
    if isinstance(to_insert, string_types):
        # 会放在</body>之前
        if re.search(r'</body>', html, flags=re.I):
            html = re.sub(r'</body>\s*\n','%s</body>\n'%to_insert, html, flags=re.I)
    return html



def insert_into_header(to_insert, html, force=False):
    # 插入到 html 页面的头部
    if not force and get_no_html_inject_in_request():
        return html
    if not to_insert:
        return html
    if isinstance(html, str_type) and isinstance(to_insert, unicode_type):
        to_insert = to_bytes(to_insert)
    if isinstance(to_insert, string_types):
        html = re.sub(r'</head>\s*<body','%s\n</head>\n<body'%to_insert, html, count=1, flags=re.I)
    return html



