#coding: utf8
from gevent import spawn
import elasticsearch
es = None


# 创建索引的返回结果
# {u'acknowledged': True}
"""
{u'error': {u'index': u'info',
  u'reason': u'already exists',
  u'root_cause': [{u'index': u'info',
    u'reason': u'already exists',
    u'type': u'index_already_exists_exception'}],
  u'type': u'index_already_exists_exception'},
 u'status': 400}
"""

bucket_info_mappings = {
    #"_source": {
    #    "enabled": True
    #},
    "properties": {
        "cursor": {
            "type": "keyword",
        }
    }
}

doc_mappings = {
    #"_source": {
    #    "enabled": False,
    #},
    "properties": {
        "bucket": {
            "index": True,
            "type": "keyword"
        },
        "path": {
            "index": True,
            "type": "keyword"
        },
        "status": {
            "index": True,
            "type": "keyword"
        },
        "title": {
            "index": True,
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart"
        },
        "raw_content": {
            "index": True,
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
            "term_vector": "with_positions_offsets"
        },
        "date": {
            "type": "date"
        },
        "position": {
            "type": "float"
        },
    }

}

doc_fields_in_es = doc_mappings['properties'].keys()


# es.index 表示是创建索引，一条记录本身就被视为 index（对象）， index_name 是一个最大的 container，可以理解为
# doc_type 相当于一个子类, 或者说类似于一个 space
# id 是一个必须的，这样就能指向一个 obj 了

# 这是一个获取一个对应索引的操作
# status_doc = es_client.get(index='info', doc_type='site', id=site_id, fields=['date'])

# 这是一个创建索引对象的操作
# es.index(index='info', doc_type='site', id=1, body={'date': datetime.datetime.utcnow()})
# es.get(index='info', doc_type='site', id=1)

# "store": True,  # 在 search 的结果中，会有这个值，get_index 则不会得到
# 因为 es 本质上，仅仅是索引的集合，主要功能是搜索，而不是存储，我们为了避免硬盘的冗余，会禁用_source的存储


def get_es_client():
    global  es
    if es is None:
        try:
            es = elasticsearch.Elasticsearch(["127.0.0.1:9200"])
        except:
            es = 0 # not allowed
    return es



def create_es_indexes():
    es = get_es_client()
    if not es:
        return
    info_result = es.indices.create(
            index = 'info',
            body = dict(
                settings={"index": {"number_of_shards":1}},
                mappings = bucket_info_mappings,
            ),
            ignore = 400
        )
    # es.indices.delete('info')
    doc_result = es.indices.create(
        index = 'doc',
        body = dict(
            settings={"index": {"number_of_shards":5}},
            mappings = doc_mappings,
        ),
        ignore = 400,
        request_timeout = 60,
    )
    print(info_result)
    print(doc_result)



def delete_es_indexes():
    es = get_es_client()
    try:es.indices.delete('info')
    except: pass
    try: es.indices.delete('doc')
    except: pass



def do_make_sure_es_indexes():
    es = get_es_client()
    if not es:
        return
    if not es.indices.exists("info") or not es.indices.exists("doc"):
        create_es_indexes()

make_sure_es_indexes_done = False
def make_sure_es_indexes(async=False):
    global make_sure_es_indexes_done
    if make_sure_es_indexes_done:
        return
    make_sure_es_indexes_done = True
    if async:
        spawn(do_make_sure_es_indexes)
    else:
        do_make_sure_es_indexes()


"""
from configs.database import db
doc = db.doc.find_one('Q0u-test.farbox.com:hello.md')
doc_id = doc.pop('_id', None)
es = get_es_client()
es.create(index='doc', doc_type='doc', id=doc_id, routing=doc['site_id'], body=doc)

es.create(index='doc', doc_type='doc', id=doc_id+'2', routing=doc['site_id']+'2', body=doc)


es.search(index='doc', doc_type='doc', fields=['sys_date'], routing='Q0u-test.farbox.com2')
"""