#coding: utf8
import re, os
from farbox_bucket.utils import smart_unicode
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils.url import unqote_url_path_to_unicode
from farbox_bucket.bucket.utils import get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.server.utils.doc_url import get_post_url_with_url_path
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.request_context_vars import get_data_root_in_request
from farbox_bucket.server.template_system.helper.get_post_with_greed import get_post_with_greed


#<span class="md_line md_line_start md_line_end"><a href="/__wiki_link/xxxxxxxx.md?type=wiki_link&hash=myid#myid" class="md_wikilink">title</a>    </span>
#<span class="md_line md_line_start md_line_end"><a href="/__wiki_tag/hello?type=wiki_link" class="md_wikilink">hello</a> 作为特殊标签？   <a href="/__tag/hello?type=wiki_link" class="md_wikilink">Hello我是title</a> 作为特殊标签？   </span>


@cache_result
def get_data_root_for_wiki():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return ""
    data_root = get_data_root_in_request()
    if data_root:
        return data_root
    site_configs = get_bucket_site_configs(bucket)
    if site_configs:
        data_root = smart_unicode(site_configs.get("posts_root") or "").strip().strip("/")
        return data_root
    else:
        return ""



def re_get_html_content_for_wiki_links_replacer(re_obj, post_doc, tag_url_prefix=None, url_root=None, url_prefix=None, hit_url_path=False):
    original_html = re_obj.group(0)
    url_href = unqote_url_path_to_unicode(re_obj.group(1))
    if "type=wiki_link" not in url_href:
        return original_html
    url_body = url_href.strip("/").split("/", 1)[-1]
    pure_url_body = re.split("[?#]", url_body)[0]
    tag_url_prefix = (tag_url_prefix or "tag").strip("/")
    if url_href.startswith("/__wiki_tag/"):
        tag = pure_url_body
        new_url_href = "/%s/%s" % (tag_url_prefix, tag)
    else:
        sub_post = get_post_with_greed(url_body, parent_doc=post_doc)
        if not sub_post:
            return original_html
        if "#" in url_body:
            hash_id = url_body.split("#", 1)[-1]
        else:
            hash_id = ""
        new_url_href = get_post_url_with_url_path(sub_post, url_prefix=url_prefix, url_root=url_root, hit_url_path=hit_url_path)
        if hash_id:
            new_url_href = "%s#%s" % (new_url_href, hash_id)
    return '<a href="%s"' % new_url_href




def re_get_html_content_for_wiki_links(post_doc, html_content=None , tag_url_prefix=None, url_root=None,
                                       url_prefix=None, hit_url_path=False):
    if not isinstance(post_doc, dict):
        return ""
    if html_content is None:
        html_content = post_doc.get("content") or ""
    new_html_content = re.sub('<a href="(/__wiki_(?:link|tag)/.*?)"', curry(re_get_html_content_for_wiki_links_replacer,
                                        post_doc = post_doc,
                                        tag_url_prefix = tag_url_prefix,
                                        url_root = url_root,
                                        url_prefix = url_prefix,
                                        hit_url_path = hit_url_path
                                        ), html_content)
    return new_html_content