# coding: utf8
from farbox_bucket.utils import string_types
from farbox_bucket.settings import DEBUG
from farbox_bucket.bucket.utils import get_bucket_last_record_id
from farbox_bucket.bucket.record.get.get import get_record
from farbox_bucket.bucket.record.get.path_related import get_bucket_markdown_record_ids
from elasticsearch.helpers import bulk


# query cursor

from .es_client import get_es_client, doc_fields_in_es, make_sure_es_indexes
from .es_utils import get_es_index_doc, search_es


def db_doc_to_es_action(bucket, doc, action_type='index'):
    # https://elasticsearch-py.readthedocs.io/en/v7.10.1/helpers.html#bulk-helpers
    if isinstance(doc, string_types):
        doc_id = doc
    else:
        doc_id = doc.pop('_id', None)
    if not doc_id or not bucket:
        return
    action = dict(
        _index = "doc",
        _op_type = action_type,
        _id = doc_id,
        _routing = bucket,
    )

    if action_type != "delete" and not isinstance(doc, dict):
        return # ignore

    if action_type != 'delete':
        # set some value
        doc["bucket"] = bucket
        path = doc.get("path")
        if not path:
            return
        doc["path"] = path.lower()
        position_value = doc.get("_order") or doc.get("order")
        if isinstance(position_value, (int, float)):
            doc["position"] = position_value

        for key in doc.keys():
            if key not in doc_fields_in_es: # pop 掉不在 es 内的 field，避免es 解析出错
                doc.pop(key, None)

        # 全小写进行索引?
        #for field in ['title', 'path', 'raw_content']:
        #    field_value = doc.get(field)
        #    if field_value and isinstance(field_value, string_types):
        #        doc[field] = field_value.lower()

        action['_source'] = doc

    return action



def force_sync_posts(bucket):
    es_client = get_es_client()
    if not es_client:
        return
    make_sure_es_indexes() # indexes 的构建，自动判断，

    bucket_markdown_record_ids = get_bucket_markdown_record_ids(bucket)
    actions = []
    ## step3, get differences and sync to es
    for record_id in bucket_markdown_record_ids:
        record = get_record(bucket, record_id)
        if not record:
            continue
        action = db_doc_to_es_action(bucket, record, action_type="index")
        if action:
            actions.append(action)
    if actions:
        bulk(es_client, actions)

    # 保存状态
    bucket_last_record_id = get_bucket_last_record_id(bucket)
    if bucket_last_record_id:
        es_client.index(index='info', id=bucket, body={'cursor': bucket_last_record_id})



def sync_posts(bucket, return_actions=False):
    es_client = get_es_client()
    if not es_client:
        return

    make_sure_es_indexes() # indexes 的构建，自动判断，

    bucket_last_record_id = get_bucket_last_record_id(bucket)

    site_status = get_es_index_doc('info', bucket)
    if site_status:
        cursor = site_status.get("cursor")
        if cursor and cursor == bucket_last_record_id:
            return  # 不需要同步，数据是一致的

    # 此处保存状态, 这样可以多个请求过来的时候，重复sync的情况
    if bucket_last_record_id:
        es_client.index(index='info', id=bucket, body={'cursor': bucket_last_record_id})
    else:
        return # ignore


    search_result = search_es(index='doc', routing=bucket,
                              q='bucket:"%s"' % bucket, fetch_all=True, per_page=1000)

    post_ids_in_es = set()
    for hit in search_result['hits']:
        doc_id = hit.get("_id")
        if doc_id: post_ids_in_es.add(doc_id)


    ## step2, get from ssdb
    bucket_markdown_record_ids = set(get_bucket_markdown_record_ids(bucket))

    # 在 es 中冗余的数据
    post_ids_in_es_to_remove = post_ids_in_es - bucket_markdown_record_ids
    post_ids_should_add_to_es = bucket_markdown_record_ids - post_ids_in_es

    actions = []
    ## step3, get differences and sync to es
    for record_id in post_ids_should_add_to_es:
        record = get_record(bucket, record_id)
        if not record:
            continue
        action = db_doc_to_es_action(bucket, record, action_type="index")
        if action:
            actions.append(action)

    for record_id in post_ids_in_es_to_remove: # 删除es中冗余的数据
        action = db_doc_to_es_action(bucket, record_id, action_type="delete")
        if action:
            actions.append(action)

    if actions:
        bulk(es_client, actions)

    if DEBUG:
        print '%s synced' % len(actions)
    if return_actions:
        return actions
    return True
