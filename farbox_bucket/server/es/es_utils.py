# coding: utf8
from __future__ import absolute_import
from elasticsearch.exceptions import NotFoundError
from .es_client import get_es_client


def get_es_index_doc(index, doc_id, return_raw=False, raise_error=False):
    es = get_es_client()
    if not es:
        return {}
    if not doc_id:
        return {}
    try:
        raw_es_doc = es.get(index=index, id=doc_id)
        if return_raw:
            return raw_es_doc
        else:
            return raw_es_doc.get('_source') or {}
    except NotFoundError, e: # 找不到 404 错误实际上
        if raise_error:
            raise e
        else:
            return {}



def search_es(index, q=None, body=None, fields=None, per_page=30, page=1, routing=None, sort=None, fetch_all=False, ):
    # q = 'raw_content:Hello'
    # q = 'site_id:"%s"'%site_id
    es = get_es_client()
    if not es:
        return {"total": 0, "hits":[]}

    start = (page-1) * per_page

    kwargs = dict(
        index = index,
        from_ = start,
        size = per_page,
    )
    if routing:
        kwargs['routing'] = routing
    if fields and isinstance(fields, (list, tuple)):
        kwargs['fields'] = fields
    else:
        # can set fields = "all", will return _source
        if not fields:
            kwargs["_source"] = False

    if q: # 基本上是关键词级别的查询了
        kwargs['q'] = q
    if body:
        kwargs['body'] = body

    if sort and body:
        if isinstance(sort, dict):
            sort = [sort]
        body['sort'] = sort

    search_result = es.search(**kwargs)

    hits = search_result['hits']

    total = hits['total']
    if isinstance(total, dict):
        total = total.get("value")
    if isinstance(total, int) and total > page*per_page and fetch_all:
        # 遍历
        next_hits = search_es(index, q, body, fields, per_page, page+1, routing, sort, fetch_all)
        hits['hits'] += next_hits['hits']

    return hits

