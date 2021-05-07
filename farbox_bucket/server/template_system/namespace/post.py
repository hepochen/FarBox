# coding: utf8
import re
from flask import abort, request

from farbox_bucket.utils import smart_unicode, to_int
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.server.utils.site_resource import get_site_config
from farbox_bucket.server.utils.record_and_paginator.paginator import auto_pg
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.request_path import get_request_offset_path_without_prefix, get_request_path_without_prefix
from farbox_bucket.server.utils.request_path import auto_bucket_url_path
from farbox_bucket.server.template_system.api_template_render import render_api_template

from farbox_bucket.bucket.utils import get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.record.utils import get_path_from_record, get_type_from_record
from farbox_bucket.bucket.record.get.mix import mix_get_record_paths
from farbox_bucket.bucket.record.get.folder import get_folder_records
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_record_by_url, get_records_by_paths, get_next_record
from farbox_bucket.bucket.record.get.tag_related import get_records_by_tag

from farbox_bucket.server.utils.record_and_paginator.paginator import get_paginator

from farbox_bucket.server.template_system.model.category import get_record_parent_category, Category
from farbox_bucket.bucket.record.get.refer_doc_related import get_records_by_post_path_back_referred, \
    get_records_by_post_path_referred
from farbox_bucket.server.template_system.helper.post_referred_docs import compute_content_with_referred_docs
from farbox_bucket.server.template_system.helper.post_compile_url_for_wiki_links import re_get_html_content_for_wiki_links

from farbox_bucket.server.template_system.namespace.data import data as get_data_namespace_object

from farbox_bucket.server.utils.request_context_vars import get_doc_in_request, set_doc_in_request



class Posts(object):
    def __init__(self):
        self.pager_name = 'posts'
        self.min_per_page = 0

    @cached_property
    def data_namespace(self):
        return get_data_namespace_object()

    def __iter__(self):
        # 返回一个迭代器，用于 for 的命令
        obj = self.list_obj
        if hasattr(obj, '__iter__'):
            return obj.__iter__()
        return obj

    def __getattr__(self, item):
        # 找不到attribute的时候，会调用getattr
        if re.match('^recent_?\d+$', item): # 获得最近的几篇文章
            limit = re.search('\d+', item).group()
            limit = to_int(limit)
            return self.get_recent(limit)

    def get_recent(self, limit=8):
        limit = to_int(limit, 8)
        limit = min(100, limit)
        post_paths = self._post_paths[:limit*2] # 取 2 倍，如果有非 public 的比较多，可能会不准确
        post_docs = get_records_by_paths(self.bucket, post_paths, ignore_marked_id=True, limit=limit)
        return post_docs
        #return get_data(type='post', limit=limit, sort='-date', with_page=False)

    def get_recent_posts(self, limit=8):
        return self.get_recent(limit)


    def get_posts_by_tag(self, tag, sort_by='-date'):
        return get_records_by_tag(self.bucket, tag, sort_by=sort_by)


    @cached_property
    def _post_paths(self):
        paths = mix_get_record_paths(bucket=self.bucket, data_type='post', data_type_reverse_sort=True)
        return paths

    @cached_property
    def length(self):
        return len(self.list_obj)

    @cached_property
    def bucket(self):
        return get_bucket_in_request_context()

    @property
    def pager(self):
        # 由于获得分页的数据对象
        # 比如可以直接调用  posts.pager....
        return get_paginator(self.pager_name, match_name=True)

    @cached_property
    def keywords(self):
        return request.args.get('s') or ''

    @cached_property
    def list_obj(self):
        pager_name = self.pager_name

        if self.keywords: # 关键词搜索放在最前面
            under = request.args.get('under') or self.posts_root
            return self.data_namespace.get_data(type='post', keywords=request.args.get('s'), path=under,
                            limit=50, pager_name=pager_name, min_limit=self.min_per_page,
                            sort='-date', status="public")

        if self.request_path.startswith('/category/'):  # 指定目录下的
            category_path = get_request_offset_path_without_prefix(1)
            records = auto_pg(bucket=self.bucket, data_type='post', pager_name=pager_name, path=category_path,
                              ignore_marked_id=True, prefix_to_ignore='_', sort_by='-date', min_limit=self.min_per_page)
            return records

        if self.request_path.startswith('/tags/') or self.request_path.startswith('/tag/'):
            _tags = get_request_offset_path_without_prefix(offset=1).strip('/')
            _tags = [tag for tag in _tags.split('+') if tag]
            records = get_records_by_tag(self.bucket, tag=_tags, sort_by='-date')
            return records

        # 默认不输出非 public 的日志
        records = auto_pg(bucket=self.bucket, data_type='post', pager_name=pager_name,
                          path = self.posts_root, ignore_marked_id=True, prefix_to_ignore='_',
                          sort_by='-date', min_limit=self.min_per_page)
        return records

    @cached_property
    def request_path(self):
        return get_request_path_without_prefix()


    @cached_property
    def posts_root(self):
        if not self.bucket:
            return ""
        site_configs = get_bucket_site_configs(self.bucket)
        root = smart_unicode(site_configs.get("posts_root", "")).strip()
        return root


    def get_post_by_url(self, url=''):
        if not self.bucket or not url:
            return None
        return get_record_by_url(self.bucket, url)


    def get_post_by_path(self, path=''):
        if not self.bucket or not path:
            return None
        return get_record_by_path(self.bucket, path)

    def get_one(self, path=None, url=None):
        if path:
            return self.get_post_by_path(path)
        else:
            return self.get_post_by_url(url)

    def find_one(self, path=None, url=None):
        return self.find_one(path=path, url=url)

    def get_current_post(self, auto_raise_404=False):
        # 在 functions.namespace.shortcut 中，将 post 本身作为一个快捷调用，可以直接调用
        doc_in_request = get_doc_in_request()
        if doc_in_request and isinstance(doc_in_request, dict) and get_type_from_record(doc_in_request) == 'post':
            return doc_in_request

        # 得到当前 url 下对应的 post
        hide_post_prefix = get_site_config('hide_post_prefix', default_value=False)
        if hide_post_prefix:  # 不包含 /post/ 的 url
            url_path = self.request_path.lstrip('/')
        else:  # 可能是/post/<url>的结构
            url_path = get_request_offset_path_without_prefix(offset=1)
        post_doc = self.get_post_by_url(url_path)

        if not post_doc and url_path and '/' in url_path:  # sub path 的对应，offset 一次，让 markdown 本身作为 template 成为可能
            url_path = '/'.join(url_path.split('/')[:-1])
            post_doc = self.get_post_by_url(url_path)

        if post_doc:  # 写入g.doc，作为上下文对象参数来处理
            set_doc_in_request(post_doc)
        else:
            if auto_raise_404:
                abort(404, 'can not find the matched post')
        return post_doc

    @cached_property
    def counts(self):
        self_list_obj = self.list_obj  # 先行调用
        if self.pager:
            return self.pager.total_count
        else:
            # /tag/ 下直接获取，没有分页的逻辑
            if self.list_obj:
                return len(self.list_obj)
            else:
                return   0


    @cached_property
    def post(self):
        return self.get_current_post(auto_raise_404=False)

    @cached_property
    def post_with_404(self):
        return self.get_current_post(auto_raise_404=True)

    @cached_property
    def next_one(self):
        record = get_next_record(bucket=self.bucket, current_record=self.post, reverse=True)
        return record

    @cached_property
    def previous_one(self):
        record = get_next_record(bucket=self.bucket, current_record=self.post, reverse=False)
        return record

    @cached_property
    def pre_one(self):
        return self.previous_one


    @cached_property
    def category(self):
        # /xxx/<category_path>
        # 根据路径，获得当前的 category 对象
        if self.request_path == '/':
            return None
        parent_path = get_request_offset_path_without_prefix(offset=1)
        return Category(parent_path)
        #return get_record_parent_category(self.post)


    @cached_property
    def categories(self):
        category_records = get_folder_records(self.bucket)
        cats = []
        for record in category_records:
            cats.append(Category(record))
        return cats

    # @cached_property
    #     def categories(self):
    #         # 取 posts_root 下的第一层的 folder
    #         folder_list = self.data_namespace.get_data(type='folder', limit=100, level=1, sort='position', path=self.posts_root)
    #         return folder_list


    def get_tag_url(self, tag):
        if isinstance(tag, (list, tuple)):
            tag = '+'.join(tag)
        url = '/tag/%s' % smart_unicode(tag)
        return auto_bucket_url_path(url)

    def tag_url(self, tag):
        return self.get_tag_url(tag)


    def set_min_per_page(self, min_per_page):
        if isinstance(min_per_page, int) and min_per_page >= 0:
            self.min_per_page = min_per_page
        return ''  # return nothing


    def search(self, keywords=None, limit=30, sort='-date'):
        # 全文检索，从而得到post_list
        # keywords 可以是字符串，也可以是 list/tuple
        if not keywords:
            return []
        limit = to_int(limit, 30)
        if isinstance(keywords, (tuple, list)):
            try: keywords = ' '.join(keywords)
            except: return []
        if not keywords:
            return []
        pager_name = 'search_posts'
        return self.data_namespace.get_data(type='post', keywords=keywords, pager_name=pager_name,
                                            min_limit=self.min_per_page, limit=limit, sort=sort)

    def search_in_html(self, base_url='', under='', just_js=False, **kwargs):
        # 产生搜索的HTML代码片段
        return render_api_template('search_posts.jade', search_base_url=base_url,
                                    search_under=under, just_js=just_js, **kwargs)


    def get_content_with_referred_docs(self, doc, for_wiki_link=True, tag_url_prefix=None, show_date=True, url_prefix=None, url_root=None, hit_url_path=True):
        # tag_url_prefix is for wiki_links only
        # 不替换 doc["content"] 避免后续这个内容会在其它地方用到而出问题
        if not isinstance(doc, dict):
            return ""
        html_content = doc.get("content") or ""
        if for_wiki_link: # 这个先处理
            html_content = re_get_html_content_for_wiki_links(doc, html_content=html_content,
                                                         tag_url_prefix = tag_url_prefix,
                                                         url_prefix = url_prefix,
                                                         url_root = url_root,
                                                         hit_url_path = hit_url_path)
        html_content = compute_content_with_referred_docs(doc, html_content=html_content, show_date=show_date, url_prefix=url_prefix,
                                                     url_root=url_root, hit_url_path=hit_url_path)
        return html_content

    def get_content_for_wiki_link(self, doc, tag_url_prefix=None, url_prefix=None, url_root=None, hit_url_path=True,):
        content = re_get_html_content_for_wiki_links(doc, tag_url_prefix=tag_url_prefix, url_prefix=url_prefix,
                                           url_root=url_root, hit_url_path=hit_url_path)
        return content


    def get_referred_docs(self, doc=None): # 本文引用的 docs
        doc = doc or self.get_current_post(auto_raise_404=False)
        if not doc:
            return []
        else:
            return get_records_by_post_path_referred(self.bucket, get_path_from_record(doc))


    def get_referred_back_docs(self, doc=None): # 引用了本文的 docs
        doc = doc or self.get_current_post(auto_raise_404=False)
        if not doc:
            return []
        else:
            return get_records_by_post_path_back_referred(self.bucket, get_path_from_record(doc))




@cache_result
def posts():
    return Posts()


@cache_result
def post():
    posts_namespace = posts()
    return posts_namespace.post # post_with_404
