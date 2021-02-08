# coding: utf8
import re
from gevent import spawn, Timeout
from flask import request
from farbox_bucket.settings import sentry_client
from farbox_bucket.utils import smart_str, to_int, to_date, string_types
from farbox_bucket.bucket.record.get.get import get_records_by_ids, get_record
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request
from .es_client import get_es_client
from .es_sync_db_data import sync_posts
from .es_utils import search_es

ALLOWED_SEARCH_FIELDS = ['title', 'raw_content']

def to_sort_str(sort):
    default_sort = 'desc'
    if isinstance(sort, string_types):
        sort = smart_str(sort)
        if sort not in ['desc', 'asc']:
            sort = default_sort
    elif isinstance(sort, int):
        sort = 'desc' if sort <0 else 'asc'
    else:
        sort = default_sort
    return sort


def es_search_posts(bucket, keywords, sort=None, status=None, path='', limit=None, page=1,
                    search_fields=None, date_start=None, date_end=None, print_query=False, should_sync_es=True):
    # 异步进行一次同步（从Mongodb到ES)
    # 确保一次request中只有一次sync的执行

    if should_sync_es:
        # 在 web app 应用时候的调用，不然会产生异常
        try:
            search_sync_is_blocked = getattr(request, 'search_sync_block', None)
        except:
            search_sync_is_blocked = True
        if search_sync_is_blocked:
            # 其它函数中已经请求同步了 或者是不支持读取 request 的（比如直接非 web 形式调用）
            sync_job = None
        else:
            sync_job = spawn(sync_posts, bucket)
            request.search_sync_block = True

        if sync_job:
            # 有0.5秒的等待时间
            sync_in_current_request = False
            try:
                synced = sync_job.get(block=True, timeout=0.5)
                sync_in_current_request = True
                if synced: # 虽然已经同步了，但可能存在数据还没有到 es 索引完成的状态
                    set_not_cache_current_request()
            except Timeout:
                # 搜索的同步没有完成，缓存策略为 no，即不缓存
                set_not_cache_current_request()

    page = to_int(page, 1)
    limit = to_int(limit, default_if_fail=3)
    if isinstance(keywords, (tuple, list)):
        keywords = ' '.join(keywords)

    if not keywords or not isinstance(keywords, string_types):
        return 0, []

    # 组装查询条件
    must = []
    filters = [{'term': {'bucket': bucket}}]

    # 获取查询的字段
    if isinstance(search_fields, string_types):
        search_fields = [search_fields]
    if isinstance(search_fields, (tuple, list)):
        _search_fields = [field for field in search_fields if field in ALLOWED_SEARCH_FIELDS]
    else:
        _search_fields = ["title", "raw_content"]

    # keywords
    keywords = keywords[:50].strip() # max_length 50!
    keywords = re.sub(r'[{}@$()\[\]/?*~]', ' ', keywords) # 去掉一些非法字符
    if not keywords:
        return 0, []

    #keywords = keywords.lower() # 全部转为小写

    keywords = re.sub(r'( or |\|)', ' OR ', keywords, flags=re.I)
    keywords = re.sub(r'( and |\+)', ' AND ', keywords, flags=re.I)
    must.append(
        {
            'query_string':
                {
                    'allow_leading_wildcard': False,
                    'default_operator': 'AND',
                    'fields': _search_fields,
                    'minimum_should_match': '100%',
                    'query': keywords
                }
        }
    )

    if not status:
        status = 'public'
    if status and isinstance(status, basestring) and status!='all':
        must.append({'term': {'status': status}})

    path = path or '/'
    path = path.lstrip('/').lower()
    if path:
        # 指定了 path
        #must.append({'prefix': {'path': {'prefix': path}}})
        must.append({'prefix': {'path': {'value': path}}})


    if sort == 'position':
        es_sort = {"position": {"order": 'asc'}}
    elif sort == '-position':
        es_sort = {"position": {"order": 'desc'}}
    elif sort == 'date':
        es_sort = {"date": {"order": 'asc'}}
    elif sort == '-date':
        es_sort = {"date": {"order": 'desc'}}
    elif sort is not None:
        # 按照 date 的排序
        sort = to_sort_str(sort)
        es_sort = {"date":{"order": sort}}
    else:
        es_sort = None

    # 日期范围
    date_start = to_date(date_start)
    date_end = to_date(date_end)
    if date_start:
        must.append(
            {'range': {'date': {'from': date_start, 'include_lower': False}}}
        )
    if date_end:
        must.append(
            {'range': {'date': {'include_upper': False, 'to': date_end}}}
        )

    search_query = dict(query={'bool': {'must': must, 'filter': filters}})

    # 高亮的逻辑
    search_query["highlight"] = {
        "pre_tags": ["<span class=keyword1>", "<span class=keyword2>"],
        "post_tags": ["</span>", "</span>"],
        "fields": {
            "title": {},
            "raw_content": {}
        }
    }

    if print_query:
        print(search_query)

    search_result = search_es(index='doc', page=page, per_page=limit,
                              body=search_query, routing=bucket, sort=es_sort)

    total = search_result['total']
    if isinstance(total, dict):
        total = total.get("value")
    hits = search_result['hits'] or []
    post_ids_with_highlight = []
    post_ids = []
    for hit in hits:
        hit_post_id = hit.get('_id')
        highlight_result = hit.get("highlight") or {}
        if hit_post_id and hit_post_id not in post_ids:
            post_ids.append(hit_post_id)
            post_ids_with_highlight.append([hit_post_id, highlight_result])


    return total, post_ids_with_highlight



def get_one_post_by_es(bucket, keywords, under=None):
    if not bucket:
        return None
    total, posts = search_posts(bucket=bucket, keywords=keywords, limit=1, page=1, path=under,
                                search_fields=["title", "path", "raw_content"], should_sync_es=False)
    if posts:
        return posts[0]
    else:
        return None


def search_posts(bucket, keywords, sort=None, status=None, path='', limit=None, page=1,
                    search_fields=None, date_start=None, date_end=None,  return_count=False, should_sync_es=True):
    es_client = get_es_client()
    if not es_client: # es is not valid
        return []
    try:
        total, post_ids_with_highlight =  es_search_posts(bucket, keywords, sort=sort, status=status, path=path,
                                           limit=limit, page=page, search_fields=search_fields,
                                           date_start = date_start, date_end = date_end, should_sync_es=should_sync_es)
        if return_count: # 直接返回匹配的数量就可以了
            return total
    except:
        total = 0
        posts = []
        sentry_client.captureException()
        set_not_cache_current_request()
    else:
        post_ids_with_highlight = post_ids_with_highlight[:100] # 最多返回的数据量
        posts = []
        for (post_id, highlight_result) in post_ids_with_highlight:
            post = get_record(bucket, post_id)
            if post:
                highlight = {}
                keyword_title_list = highlight_result.get("title")
                if keyword_title_list:
                    if isinstance(keyword_title_list, (list, tuple)):
                        highlight["title"] = keyword_title_list[0]
                    else:
                        highlight["title"] = keyword_title_list
                keyword_content_list = highlight_result.get("raw_content")
                if keyword_content_list:
                    if isinstance(keyword_content_list, (list, tuple)):
                        keyword_content_list_length = len(keyword_content_list)
                        if keyword_content_list_length == 1:
                            content = keyword_content_list[0]
                            if "---\n" in content:
                                content = content.rsplit("---\n", 1)[-1]
                            highlight["content"] = content
                        elif keyword_content_list_length >= 2:
                            highlight["content_list"] = keyword_content_list
                    else:
                        highlight["content"] = keyword_content_list
                post["highlight"] = highlight
                posts.append(post)
    return total, posts





