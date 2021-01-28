#coding: utf8
from __future__ import absolute_import
import re
from farbox_bucket.utils import smart_unicode, make_content_clean, UnicodeWithAttrs
from farbox_markdown.compile_md import fix_relative_image_path
import cgi

# backend也有用到,所以放在farbox.utils中

def html_escape(content):
    escaped_content = cgi.escape(content)
    escaped_content = make_content_clean(escaped_content)
    # escaped_content = escaped_content.replace('\x08', '').replace('\x07', '') # 去除 \a \b 标记
    return escaped_content

def linebreaks(value, post_path=None, render_markdown_image=False):
    """Converts newlines into <p> and <br />s."""
    # post_path 是处理图片本身的相对路径，这样就可以处理Markdown语法的图片了
    value = re.sub('<.*?[^>]$','', value) #避免尾行图片（源码）被截断
    value = re.sub(r'\r\n|\r|\n', '\n', value)
    paras = re.split('\n{2,}', value)
    new_paras = []
    for p in paras:
        p = "\n\n".join([u"<p>%s</p>"%line for line in re.split('\n',p)])
        p = u'<div class="p_part">%s</div>' %p
        new_paras.append(p)
    html = u'\n\n'.join(new_paras)
    if post_path or render_markdown_image:
        html = re.sub(r'!\[(.*?)\]\(([^")]+)\)', '<img title="\g<1>" src="\g<2>"/>', html) # 将Markdown  图片语法的转为 html
    if post_path:
        html = fix_relative_image_path(post_path, html) # 相对路径的图片需要进行转化
    return html




def html_to_text(content, keep_a_html=False, remove_a=True, keep_images=False, quote_tags=False):
    # keep_a_html 可以保留 a 元素 的完整逻辑
    # remove_a 表示整个A 元素删除，反之则是转为普通的文本
    content = re.sub(r'<!--.*?-->', '', content) # 先去除HTML的注释
    content = re.sub('<div class="linenodiv">.*?</div>', '', content, flags=re.S) # 去代码高亮
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.I|re.S)
    content = re.sub(r'</p>\s*<p>', '\n\n', content, flags=re.I|re.S)
    if keep_images:
        content = re.sub('(<img)([^<]+)(/?\s*>)', '&LT;img\g<2>/&GT;', content) # 保护图片代码

    if keep_a_html:
        remove_a = False
    if remove_a: # 会把 a 元素整体删除..
        content = re.sub(r'<a[^<]+>([^<]+)</a>', '', content, re.I|re.S)
    if keep_a_html: # 保留原始的 A 元素
        content = re.sub(r'(<)(a[^<]+)(>)([^<]+)(</a>)', '&LT;\g<2>&GT;\g<4>&LT;/a&GT;', content, re.I|re.S)

    content = re.sub(r'</?[^<]+?>', '', content).strip() # 去tag 标签
    #content = html_unescape(content)

    if quote_tags:
        content = content.replace('<', '&lt;').replace('>', '&gt;')


    # 还原 A  & IMG 元素
    content = content.replace('&LT;', '<').replace('&GT;', '>')


    content = re.sub(r'\n +', '\n', content)

    return content



def cut_content_by_words(content, max_words, mark=u'...'):
    if not isinstance(max_words, int):
        return content
    if max_words < 1:
        return content
    if max_words > 2000:
        max_words = 2000 # 最大不能超过这个，不然性能问题
    content = smart_unicode(content)
    iter_found = re.finditer(ur'[\w\-_/]+|[\u1100-\ufde8]', content)
    n = 0
    end = 0
    for i in iter_found:
        end = i.end()
        n += 1
        if n >= max_words:
            break
    if end:
        new_content = content[:end]
        if len(content) > end:
            mark = smart_unicode(mark)
            new_content += mark
            new_content = UnicodeWithAttrs(new_content)
            new_content.has_more = True
        return new_content
    else:
        return content



HTML_C = re.compile(r'</?[^<]+?>')
def limit(content, length=None, mark='......', keep_images=True, words=None, post_path=None, remove_a=False, keep_a_html=False, ignore_first_tag_name=None):
    # like patch...
    # smartpage 中声明 css的
    # post_path 指定的，则会尝试解析 Markdown （插图）语法的逻辑
    content = re.sub('<div class="codehilite code_lang_css  highlight">.*?<!--block_code_end-->', '', content, flags=re.S)

    if ignore_first_tag_name:
        # 忽略掉首个 dom 元素，一般是 blockquote
        if isinstance(ignore_first_tag_name, (str, unicode)) and re.match(r'[a-z]+$', ignore_first_tag_name, re.I):
            content = content.strip()
            content = re.sub(r'^<%s[^<>]*>.*?</%s>'%(ignore_first_tag_name, ignore_first_tag_name), '', content, flags=re.I|re.S)

    if HTML_C.search(content): #如果有html的代码，则进行平文本转义
        content = html_to_text(content, keep_images=keep_images, remove_a=remove_a, keep_a_html=keep_a_html, quote_tags=True)
    if not length and not words: # 长度都没有说声明
        output = content
        has_more = False
    else:
        if words and isinstance(words, int):
            output = cut_content_by_words(content, words, mark=mark)
            has_more = getattr(output, 'has_more', False)
        else:
            output = content[0:length]
            if len(content) > length:
                has_more = True
                if mark:
                    output += smart_unicode(mark)
            else:
                has_more = False
    output = linebreaks(output, post_path=post_path)
    content = UnicodeWithAttrs(output)
    content.has_more = has_more
    content.without_pics = re.sub('<img[^<]+/\s*>', '', output) #去掉img节点
    content.without_pic = content.no_pic = content.without_pics

    return content