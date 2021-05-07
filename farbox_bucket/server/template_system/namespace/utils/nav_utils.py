# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import smart_unicode, get_value_from_data, auto_type
from flask import request
from farbox_bucket.bucket.record.get.path_related import has_markdown_record_by_path_prefix
from farbox_bucket.bucket.record.get.path_related import get_json_content_by_path
from farbox_bucket.bucket.utils import get_bucket_pages_configs, get_bucket_site_configs
from farbox_bucket.server.utils.request_path import auto_bucket_url_path


# nav_data is a list, item in it is a dict, like [{name:xxx, url:xxxx}]

def get_nav_items_from_site_configs(bucket):
    # nav_configs & user_nav_disabled 两个属性，是在线编辑 nav 时写入 configs/nav_config.json 中的
    if not bucket:
        return []
    nav_config = get_json_content_by_path(bucket, 'nav.json') or {}
    if not nav_config:
        return []
    site_nav_configs = nav_config.get('nav_configs') or []
    if nav_config.get('user_nav_disabled', False):
        # 用户(拖拽）自定义的导航被禁用了
        site_nav_configs = []
    if not isinstance(site_nav_configs, (list, tuple)):
        return []
    nav_items = []
    for nav_item in site_nav_configs:
        if isinstance(nav_item, dict) and 'name' in nav_item and 'url' in nav_item:
            nav_items.append(nav_item)
    return nav_items


"""
---
title: CaiCai's Photos
nav:
    - Home: /
    - Other: /
    - 中文: /
sort: -date
---
"""
def get_nav_items_from_doc(doc):
    # 在 metadata 中声明了 nav，并且本身是一个 list，子元素为 dict类型
    if not doc:
        return []
    nav_items = []
    nav_configs_in_doc = get_value_from_data(doc, 'metadata.nav')
    if not nav_configs_in_doc or not isinstance(nav_configs_in_doc, (list, tuple)):
        return []
    for raw_nav_item in nav_configs_in_doc:
        if isinstance(raw_nav_item, dict) and raw_nav_item:
            k, v = raw_nav_item.items()[0]
            if isinstance(k, basestring) and isinstance(v, basestring):
                nav_item = dict(name=k, url=v)
                nav_items.append(nav_item)
    return nav_items



def get_auto_nav_items(bucket): # 自动生成的
    pages_configs = get_bucket_pages_configs(bucket)
    nav_items = []
    homepage_url = '/'
    if request.args.get('status') == 'loaded':
        homepage_url = '/?status=loaded'
    homepage_nav_item = dict(name='Home', url=homepage_url)
    nav_items.append(homepage_nav_item)

    site_configs = get_bucket_site_configs(bucket)
    albums_root = smart_unicode(site_configs.get("albums_root", "")).strip()
    if albums_root:
        nav_items.append(dict(
            name = "Album",
            url = "/album"
        ))

    wiki_configs = get_json_content_by_path(bucket, "__wiki.json", force_dict=True)
    wiki_root = wiki_configs.get("wiki_root")
    enable_wiki_nodes = auto_type(wiki_configs.get("enable_wiki_nodes", True))
    if wiki_root:
        nav_items.append(dict(
            name="Wiki",
            url="/wiki"
        ))

        if enable_wiki_nodes:
            nav_items.append(dict(
                name="Wiki Nodes",
                url="/wiki_nodes"
            ))


    if 'categories.jade' in pages_configs:
        # 有 categories.jade 的呈现
        nav_items.append(dict(
            name = 'Categories',
            url = '/categories'
        ))
    if 'archive.jade' in pages_configs: # archive 页面
        nav_items.append(dict(
            name = 'Archive',
            url = '/archive'
        ))

    if has_markdown_record_by_path_prefix(bucket, "links"):
        nav_items.append(dict(
            name='Links',
            url='/__page/links'
        ))

    if has_markdown_record_by_path_prefix(bucket, "about"):
        nav_items.append(dict(
            name='About',
            url='/__page/about'
        ))

    if has_markdown_record_by_path_prefix(bucket, "contact"):
        nav_items.append(dict(
            name='Contact',
            url='/__page/contact'
        ))


    #if 'feed.jade' in pages_configs:
    nav_items.append(dict(
    name='Feed',
    url='/feed'
    ))

    return nav_items




def deal_nav_items(nav_items):
    new_nav_items = []
    if not nav_items:
        return []
    if not isinstance(nav_items, (list, tuple)):
        return []
    for nav_item in nav_items:
        if isinstance(nav_item, dict):
            new_nav_items.append(nav_item)
        elif isinstance(nav_item, (list,tuple)) and len(nav_item)==2:
            # nav_item 是一个 list，主要是在 Template API 中调用，因为代码量会低一些
            name, url = nav_item
            new_nav_items.append(dict(
                name = smart_unicode(name),
                url = smart_unicode(url)
            ))
    return new_nav_items




def pre_nav_data(nav_data):
    if not isinstance(nav_data, (list, tuple)):
        return []
    new_nav_data = []
    for nav_item in nav_data:
        if isinstance(nav_item, dict):
            new_nav_data.append(nav_item)
        elif isinstance(nav_item, (list, tuple)) and len(nav_item) >=2:
            e1, e2 = nav_item[:2]
            if '/' in e1:
                new_nav_data.append(dict(url=auto_bucket_url_path(e1), name=e2))
            else:
                new_nav_data.append(dict(url=auto_bucket_url_path(e2), name=e1))
    return new_nav_data