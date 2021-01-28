# coding: utf8
import datetime
from farbox_bucket.server.comments.utils import get_comments_record, get_comments_by_comments_doc, to_doc_path, doc_path_to_comments_path
from farbox_bucket.utils import to_float
from farbox_bucket.utils.data import dump_csv, csv_records_to_object
from farbox_bucket.client.sync.compiler_worker import get_compiler_data_directly
from farbox_bucket.bucket.record.helper.update_record import update_record_directly




def dump_comments_to_csv_content(parent_obj_doc, comments):
    comment_keys = ['author', 'content', 'email', 'site', 'date', 'ip', 'reply']
    utc_offset = to_float(parent_obj_doc.get('_utc_offset'), default_if_fail=8)
    #doc_path = to_doc_path(parent_obj_doc)
    #comments_path = doc_path_to_comments_path(doc_path)  # 评论的文档存储路径
    csv_records = [comment_keys]
    for comment in comments:
        csv_record = []
        for key in comment_keys:
            value = comment.get(key) or ''
            if isinstance(value, datetime.datetime):
                value = value + datetime.timedelta(0, utc_offset * 3600)
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            csv_record.append(value)
        csv_records.append(csv_record)
    csv_content = dump_csv(csv_records)
    return csv_content



def add_new_comment_to_doc(bucket, parent_obj_doc, comment=None, comments=None):
    # comment is a dict, should add to comments_doc.comments
    # 也有可能 comments_doc 还不存在
    if not bucket:
        return
    if not parent_obj_doc:
        return

    doc_path = to_doc_path(parent_obj_doc)

    if not comments and comment:
        # 如果没有给出 comments，那么就获取 comments 并添加 comment
        comments_doc = get_comments_record(bucket, doc_path) or {}
        comments = comments_doc.get('objects') or []
        if isinstance(comments, tuple):
            comments = list(comments)
        comments.append(comment)
    elif comments and comment:
        comments.append(comment)

    if not comments:
        return # ignore

    comments_path = doc_path_to_comments_path(doc_path)  # 评论的文档存储路径
    csv_content = dump_comments_to_csv_content(parent_obj_doc, comments)
    raw_record = get_compiler_data_directly(relative_path=comments_path, content=csv_content)

    update_record_directly(bucket, raw_record)




















