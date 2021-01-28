#coding: utf8
from __future__ import absolute_import
import requests
from pyquery import PyQuery as pq
from utils import smart_unicode
from utils.md.markdownify import markdownify as md
import re
from utils.functional import curry

# url = http://mp.weixin.qq.com/s?__biz=MjM5ODIyMTE0MA==&mid=205238326&idx=1&sn=4573f34488139107ef3431cce890669b&3rd=MzA3MDU4NTYzMw==&scene=6#rd


def get_first_dom(d, tag):
    doms = d(tag)
    if doms:
        dom = d(doms[0])
        return dom
    else:
        return doms

def get_content_from_wechat_url(url):
    res = requests.get(url)
    html_content = smart_unicode(res.content)
    d = pq(html_content)
    rich_content_dom = get_first_dom(d, '.rich_media_content')
    if rich_content_dom:
        raw_content = rich_content_dom.html()
        raw_content = re.sub('(<img .*?)(data-src=)', '\g<1>src=', raw_content)
    else:
        raw_content = ''
    content = md(raw_content).strip(' \n')
    content = re.sub(u'\n([* 　\t]*\n)+', '\n\n', content)
    content = re.sub(u'\n(>[ 　]*\n)+', '\n', content) # blank quote
    title = get_first_dom(d, '.rich_media_title').text()
    cover = ''
    cover_dom = get_first_dom(d, '.rich_media_thumb_wrp')
    if cover_dom:
        cover_dom_html = cover_dom.html() or ''
        cover_c =  re.search('(https?://.*?)[\'"]', cover_dom_html)
        if cover_c:
            cover = cover_c.groups()[0]
    date = get_first_dom(d, '#post-date').text() or ''
    meta = "---\ntitle: %s\noriginal_url: %s\noriginal_date: %s\n---\n\n" % (title, url, date)
    if cover:
        content = '![](%s)\n\n' % cover + content
    # add source link now
    site_title = get_first_dom(d, 'title').text() or ''
    full_content = meta + content + '\n\n[Source From %s](%s)' % (site_title, url)

    # end
    return full_content


def get_content_from_wechat_url_by_cache(url):
    #key = 'wechat_url_'+get_hash_key(url)
    #data_func = curry(get_content_from_wechat_url, url=url)
    #return cache_client.auto_cache(key, data_func, zipped=True, expiration=6*60*60) # cache 6 hours
    return get_content_from_wechat_url(url)


