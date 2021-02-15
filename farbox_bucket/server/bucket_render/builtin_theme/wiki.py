# coding: utf8
import re
from flask import request, abort
from farbox_bucket.utils import smart_unicode, get_value_from_data, string_types, auto_type
from farbox_bucket.utils.path import get_just_name
from farbox_bucket.bucket.utils import get_bucket_posts_info, get_bucket_in_request_context
from farbox_bucket.bucket.record.utils import get_path_from_record, get_type_from_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_json_content_by_path, get_records_by_paths
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.server.template_system.namespace.data import Data
from farbox_bucket.server.utils.request_path import get_request_path, get_offset_path
from farbox_bucket.server.utils.response import force_response
from farbox_bucket.utils.md_related.filter_posts_info import filter_and_get_posts_link_points_info
from farbox_bucket.bucket.record.get.tag_related import get_records_by_tag

from farbox_bucket.server.template_system.namespace.data import data as get_data_namespace
from farbox_bucket.server.template_system.model.category import Category
from farbox_bucket.utils.path import get_relative_path
from farbox_bucket.server.utils.record_and_paginator.paginator import auto_pg
from farbox_bucket.server.utils.request_context_vars import set_data_root_in_request


def get_wiki_url_for_doc(wiki_root, doc):
    if not isinstance(wiki_root, string_types) or not isinstance(doc, dict):
        return ""
    wiki_root = wiki_root.strip("/")
    doc_type = get_type_from_record(doc)
    doc_path = get_path_from_record(doc)
    relative_path = get_relative_path(doc_path.lower().strip("/"), wiki_root, return_name_if_fail=False)
    if not relative_path:
        return ""
    if doc_type == "post":
        return "/wiki/post/%s" % relative_path
    else:
        return "/wiki/category/%s" % relative_path



def show_wiki_nodes_as_sub_site():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return
    request_path = get_request_path().strip("/")
    if not re.match("wiki_nodes(/|$)", request_path):
        return
    wiki_configs = get_json_content_by_path(bucket, "__wiki.json", force_dict=True)
    enable_wiki_nodes = auto_type(wiki_configs.get("enable_wiki_nodes", True))
    if not enable_wiki_nodes:
        return
    wiki_root = smart_unicode(wiki_configs.get("wiki_root", ""))
    if not wiki_root:
        return
    wiki_root = wiki_root.strip("/")
    wiki_title = wiki_configs.get("wiki_title") or get_just_name(wiki_root, for_folder=True)
    path = request.values.get("path", "").strip("/")
    if request.values.get("type") == "data":
        # return json data
        wiki_root = wiki_root.lower()
        under = "%s/%s" % (wiki_root, path)
        posts_info = get_bucket_posts_info(bucket)
        data = filter_and_get_posts_link_points_info(posts_info, under=under)
        nodes = data.get("nodes")
        if nodes:
            for node in nodes:
                node_id = node.get("id")
                if node_id and isinstance(node_id, string_types):
                    if node_id.startswith("#"):
                        tag = node_id.lstrip("#")
                        url = "/wiki/tag/%s" % tag
                        node["url"] = url
                    else:
                        relative_path = get_relative_path(node_id.strip("/"), wiki_root, return_name_if_fail=False)
                        if relative_path:
                            url = "/wiki/post/%s" % relative_path
                            node["url"] =  url
        return force_response(data)
    else:
        return render_api_template("builtin_theme_wiki_nodes.jade", wiki_title=wiki_title)



def show_wiki_as_sub_site():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return
    request_path = get_request_path().strip("/")
    if not re.match("wiki(/|$)", request_path):
        return
    wiki_configs = get_json_content_by_path(bucket, "__wiki.json", force_dict=True)
    wiki_root = smart_unicode(wiki_configs.get("wiki_root", ""))
    if not wiki_root:
        return
    set_data_root_in_request(wiki_root) # set data_root to request
    wiki_root = wiki_root.strip("/")
    wiki_title = wiki_configs.get("wiki_title") or get_just_name(wiki_root, for_folder=True)
    wiki_root = wiki_root.lower()

    kwargs = dict(wiki_root=wiki_root, wiki_title=wiki_title, wiki_configs=wiki_configs)

    if re.match("wiki/?$", request_path):
        # index
        docs = []
        user_categories = wiki_configs.get("categories")
        if not isinstance(user_categories, (list, tuple)):
            user_categories = []
        for user_category in user_categories:
            if not isinstance(user_category, dict): continue
            category_path = user_category.get("path")
            summary = smart_unicode(user_category.get("summary") or "")
            icon = smart_unicode(user_category.get("icon") or "")
            doc = get_record_by_path(bucket=bucket, path=category_path)
            if not doc:
                category_path = "%s/%s" % (wiki_root, category_path.strip("/"))
                doc = get_record_by_path(bucket=bucket, path=category_path)
                if not doc:
                    continue
            doc_type = get_type_from_record(doc)
            if doc_type not in ["post", "folder"]:
                continue
            doc["icon"] = icon or get_value_from_data(doc, "metadata.icon")
            doc["summary"] = summary or get_value_from_data(doc, "metadata.summary")
            docs.append(doc)
        if not docs: # by default
            docs = Data.get_data(type='folder', level=1, limit=50, with_page=False, path=wiki_root)

        # 处理 url, 取 relative
        index_docs = []
        for doc in docs:
            wiki_url = get_wiki_url_for_doc(wiki_root, doc)
            if not wiki_url:
                continue
            doc["wiki_url"] = wiki_url
            index_docs.append(doc)

        return render_api_template("builtin_theme_knowbase_index.jade", docs=index_docs, **kwargs)

    elif re.match("wiki/tag/", request_path):
        current_tag = get_offset_path(request_path, 2)
        if not current_tag:
            abort(404, "no tag?")
        docs = get_records_by_tag(bucket, current_tag, sort_by="-date")
        for doc in docs:
            doc["wiki_url"] = get_wiki_url_for_doc(wiki_root, doc)
        return render_api_template("builtin_theme_knowbase_tag.jade", current_tag=current_tag, docs=docs, **kwargs)

    elif re.search("wiki/search(/|$)", request_path):
        keywords = request.values.get("s")
        data_namespace = get_data_namespace()
        docs = data_namespace.get_data(bucket=bucket, keywords=keywords, pager_name="wiki", path=wiki_root,
                                       sort_by='-date', min_limit=8)
        for doc in docs:
            doc["wiki_url"] = get_wiki_url_for_doc(wiki_root, doc)
        return render_api_template("builtin_theme_knowbase_search.jade", docs=docs, **kwargs)

    elif re.match("wiki/category/", request_path):
        # category
        category_path = get_offset_path(request_path, 2).lower()
        wiki_nodes_url = "/wiki_nodes?path=%s" % category_path
        category_path = "%s/%s" % (wiki_root, category_path)
        folder_doc = get_record_by_path(bucket, category_path)
        enable_wiki_nodes = auto_type(wiki_configs.get("enable_wiki_nodes", True))
        if not enable_wiki_nodes:
            wiki_nodes_url = ""
        if not folder_doc or get_type_from_record(folder_doc) != "folder":
            abort(404, "no category found")
        else:
            category = Category(folder_doc)
            docs = auto_pg(bucket=bucket, data_type="post", pager_name="wiki", path=category.path,
                           ignore_marked_id=True, prefix_to_ignore='_', sort_by='-date', min_limit=8)
            for doc in docs:
                doc["wiki_url"] = get_wiki_url_for_doc(wiki_root, doc)
            return render_api_template("builtin_theme_knowbase_category.jade", category=category, docs=docs,
                                       wiki_nodes_url=wiki_nodes_url, **kwargs)

    elif re.match("wiki/post/", request_path):
        # detail
        doc_path = get_offset_path(request_path, 2)
        doc_path = "%s/%s" % (wiki_root, doc_path)
        doc = get_record_by_path(bucket, doc_path)
        if not doc:
            abort(404, "no doc found")
        else:
            return render_api_template("builtin_theme_knowbase_post.jade", doc=doc, **kwargs)








