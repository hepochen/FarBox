# coding: utf8
from __future__ import absolute_import
import re

def re_html_for_wechat_public(html_content):
    # html 源代码需要进行必要的转义，处理为微信公众后台能正常使用的状态
    html_content = re.sub(r'font-family:[^,;]*?,[^;]*?;', 'font-family:sans-serif;', html_content, flags=re.I)
    # 不处理pre内的话，微信上换行会被吃掉
    pres = re.findall('<pre[^<>]*?>.*?</pre>', html_content, re.I|re.S)
    for pre in pres:
        html_content = html_content.replace(pre, re.sub(r'\r?\n', '<br>', pre), 1)
    return html_content
