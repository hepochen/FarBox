# coding: utf8
from flask import abort, redirect, request
from farbox_bucket.utils import smart_unicode
from farbox_bucket.server.web_app import app
from farbox_bucket.bucket.utils import  set_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_json_content_by_path
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request
from farbox_bucket.server.utils.doc_url import get_doc_url, get_post_url_with_url_path
from farbox_bucket.server.template_system.helper.get_post_with_greed import get_post_with_greed
from farbox_bucket.server.bucket_render.builtin_theme.wiki import get_wiki_url_for_doc



def get_wiki_root(bucket):
    wiki_configs = get_json_content_by_path(bucket, "__wiki.json", force_dict=True)
    wiki_root = smart_unicode(wiki_configs.get("wiki_root", ""))
    return wiki_root


@app.route("/__wiki_tag/<path:tag>")
def show_wiki_tag_fallback(tag):
    bucket = get_bucket_from_request()
    if not bucket:
        abort(404)
    set_bucket_in_request_context(bucket)
    wiki_root = get_wiki_root(bucket)
    if wiki_root:
        new_url = "/wiki/tag/%s?type=wiki_link" % tag
    else:
        new_url = "/tag/%s?type=wiki_link" % tag
    return redirect(new_url)



@app.route("/__wiki_link/<path:post_path>")
def show_wiki_link_fallback(post_path):
    bucket = get_bucket_from_request()
    if not bucket:
        abort(404)
    if "?" in request.url:
        url_GET_part = request.url.split("?")[-1]
        post_path = "%s?%s" % (post_path, url_GET_part)
    wiki_root = get_wiki_root(bucket)
    post_doc = get_post_with_greed(url_body=post_path)
    if not post_doc:
        return abort(404, "post is not found")
    if wiki_root:
        post_url = get_wiki_url_for_doc(wiki_root, post_doc)
    else:
        post_url = get_doc_url(post_doc)
    if not post_url:
        return abort(404, "post is not found, post_url get failed")
    else:
        return redirect(post_url)


