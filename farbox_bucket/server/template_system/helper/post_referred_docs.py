# coding: utf8
import re, os
from farbox_bucket.utils.functional import curry
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.utils.url import unqote_url_path_to_unicode
from farbox_bucket.server.utils.doc_url import get_post_url_with_url_path
from farbox_bucket.server.template_system.helper.get_post_with_greed import get_post_with_greed

def re_sub_for_referred_docs(re_obj, show_date=True,  post_doc=None, url_root=None, url_prefix=None, hit_url_path=False):
    #prefix = re_obj.group(1)
    url = re_obj.group(2)
    url = unqote_url_path_to_unicode(url)
    original_html = re_obj.group(0)
    html_before_a = re_obj.group(1)
    html_after_a = re_obj.group(3)
    if "?x" in url:
        inline = True
    else:
        if html_before_a and html_before_a.startswith("<span ") and html_before_a.endswith(">") and html_after_a:
            inline = False
        else:
            inline = True
    if "://" in url:
        return original_html
    if "original=yes" in url:
        return original_html
    else:
        sub_post = get_post_with_greed(url, parent_doc=post_doc)
        if not sub_post:
            return original_html
        if "#" in url:
            hash_id = url.split("#", 1)[-1]
        else:
            hash_id = ""
        post_url = get_post_url_with_url_path(sub_post, url_prefix=url_prefix, url_root=url_root, hit_url_path=hit_url_path)
        return render_api_template("builtin_api_referred_post.jade",
                                   sub_post = sub_post,
                                   show_date = show_date,
                                   post_url = post_url,
                                   hash_id = hash_id, inline=inline)





def compute_content_with_referred_docs(post_doc, html_content=None, show_date=True, url_prefix=None, url_root=None, hit_url_path=False):
    path = get_path_from_record(post_doc)
    if not path:
        return ""
    content = html_content or post_doc.get("content") or ""
    new_content = re.sub(r"""(<[^<>]+>)?<a [^<>]*?href=['"](.*?)['"][^<>]*?>.*?</a>(</\w+>|<\w+ */>)?""",
                         curry(re_sub_for_referred_docs, show_date=show_date, post_doc=post_doc,
                               url_prefix=url_prefix, url_root=url_root, hit_url_path=hit_url_path, ),
           content)
    return new_content

