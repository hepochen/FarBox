# coding: utf8
from farbox_bucket.bucket.utils import get_bucket_last_record_id
from .es_client import get_es_client, doc_fields_in_es, make_sure_es_indexes
from .es_utils import get_es_index_doc, search_es




def get_es_status_for_bucket(bucket):
    es = get_es_client()
    status = dict(
        db_last_id = get_bucket_last_record_id(bucket),
        es_is_valid = False if not es else True,
    )
    if not es:
        return status
    es_info = get_es_index_doc('info', bucket)
    if es_info:
        status["es_cursor"] = es_info.get("cursor")
    try:
        es_count_result = es.count(q='bucket:"%s"' % bucket, routing=bucket)
        es_count = es_count_result.get("count") or 0
    except:
        es_count = 0
    status["es_count"] = es_count
    status["es_indexes_ok"] = es.indices.exists("info") and es.indices.exists("doc")

    return status