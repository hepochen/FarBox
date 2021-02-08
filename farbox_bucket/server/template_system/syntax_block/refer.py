# coding: utf8
import re
from farbox_bucket.utils.functional import curry
from farbox_bucket.server.utils.cache_for_function import cache_result



def re_sub_refer(re_obj, handler=None):
    prefix = re_obj.group(1)
    url = re_obj.group(2)
    suffix = re_obj.group(3)
    new_line = False
    if prefix and suffix:
        if prefix.startswith('<span ') and 'md_line' in prefix and suffix == '</span>':
            new_line = True
        elif re.match(r'<div[ >]', prefix) and suffix == '</div>':
            new_line = True
        elif re.match(r'<p[ >]', prefix) and suffix=='</p>':
            new_line = True
    original_html = re_obj.group(0)
    new_html = original_html

    # 三个变量，逐个试过去，懒得 inspect 了...
    try:
        new_html = handler(url, original_html, new_line)
    except TypeError:
        try: new_html = handler(url, original_html)
        except TypeError:
            try: new_html = handler(url)
            except: pass
    except:
        pass
    return new_html


def refer(handler=None, refer_type='link', **kwargs):
    caller = kwargs.pop('caller', None)
    if not caller or not hasattr(caller, '__call__'):
        return ''
    inner_html = caller()
    if not handler or not hasattr(handler, '__call__'):
        return inner_html
    if refer_type in ['image', 'images']:
        # 图片
        inner_html = re.sub(r"""(<[^<>]+>)?<img [^<>]*?src=['"](.*?)['"][^<>]*?/?>(</\w+>)?""", curry(re_sub_refer, handler=handler), inner_html)
    else:
        # 链接
        inner_html = re.sub(r"""(<[^<>]+>)?<a [^<>]*?href=['"](.*?)['"][^<>]*?>.*?</a>(</\w+>)?""", curry(re_sub_refer, handler=handler), inner_html)
    return inner_html



# demo for sub post
"""
mixin sub_post_handler(url, original_html, new_line=False)
    if not new_line
        {{original_html}}
    else
        sub_post = d.get_doc(url=url)
        if not sub_post
            {{original_html}}
        else: .post-preview.clearfix
            preview_meta_class = "with_bg post-preview--meta" if sub_post.cover else 'without_bg post-preview--meta'
            div(class=preview_meta_class)
                .post-preview--middle
                    h4.post-preview--title
                        a(href=sub_post.url)= sub_post.title
                    time.post-preview--date= sub_post.date('%Y/%m/%d')
                    section.post-preview--excerpt
                        span= sub_post.content.limit(words=20, keep_images=False).plain
            if sub_post.cover
                bg_url = sub_post.cover.resize(350, 350, fixed=True)
                .post-preview--image(style="background-image:url({{bg_url}})")
block content
    main.content(role='main'): +refer(sub_post_handler)
        article.post
            header.post-header
                h1.post-title= post.title
                section.post-meta
                    time.date.post-date= post.date.format('%B %d, %Y')
            section.post-content.markdown= post.content

            footer.post-footer
                figure.author-image
                    a.img(href='/', style="background-image:url({{site.avatar}})")

            +post.comments_as_html()
"""


## demo for image
"""
mixin sub_image_handler(url, original_html)
        +h.js_view(url)
.post_page
    .post: +refer(sub_image_handler, refer_type='image')
        header.post_meta
            date.post-date= post.date.format('%B %d, %Y')
            h1.post_title= post.title
        section.post_content.markdown= post.content
"""