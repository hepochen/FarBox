#coding: utf8
from __future__ import absolute_import
from flask import request
from farbox_bucket.utils import smart_unicode, get_md5, get_value_from_data, is_closed, string_types, to_float
from farbox_bucket.utils.date import utc_date_parse
from farbox_bucket.bucket.utils import get_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.server.avatar import get_avatar_url
from farbox_bucket.server.utils.site_resource import get_bucket_site_configs

#from dateutil.parser import parse as date_parse
import os


def to_doc_path(path_or_doc):
    if isinstance(path_or_doc, dict):
        path = path_or_doc.get('path')
    else:
        path = path_or_doc
    path = smart_unicode(path).strip('/').strip()[:500].lower()
    return path



def doc_path_to_comments_path(doc_path):
    path_without_ext = os.path.splitext(doc_path)[0]
    comments_path = '_comments/%s.csv' % path_without_ext.lower().strip('/')
    #doc_path_name = get_just_name(doc_path.lower())
    #doc_path_md5 = get_md5(doc_path)
    #comments_filename = '%s_%s_cs.csv' % (doc_path_name, doc_path_md5)
    #comments_path = 'comments/%s' % comments_filename
    return comments_path



def get_comment_avatar(author_email):
    author_email = author_email or ''
    author_email = author_email.lower()
    return get_avatar_url(author_email)


def get_comment_author_name(original_author, author_email):
    if not original_author and author_email:
        # 从 email 中进行提取
        original_author = author_email.split('@')[0].split('+')[0].title()
    return original_author



def get_comments_record(bucket, doc_path): # 已经解密了的
    comments_path = doc_path_to_comments_path(doc_path)  # 评论的文档存储路径
    comments_doc = get_record_by_path(bucket=bucket, path=comments_path)  or {} # 获得对应 comments 的 record
    if comments_doc:
        objects = comments_doc.get('objects') or []
        comments_doc['objects'] = objects
    return comments_doc




def get_comments(parent_doc, bucket=None, as_tree=None):
    bucket = bucket or get_bucket_in_request_context() or request.values.get('bucket')
    if not bucket:
        return []
    path = to_doc_path(parent_doc)

    comments_doc = get_comments_record(bucket, path)

    site_configs = get_bucket_site_configs(bucket)

    if not get_value_from_data(site_configs, "comments", default=True):
        return []

    if as_tree is None: # 自动匹配, 网站设置中对应
        comments_type = get_value_from_data(site_configs, 'comments_type') or 'tree'
        if comments_type in ['tree']:
            as_tree = True
        else:
            as_tree = False

    utc_offset = to_float(parent_doc.get('_utc_offset'), 8)

    return get_comments_by_comments_doc(comments_doc, as_tree=as_tree, utc_offset=utc_offset)



def get_comments_by_comments_doc(comments_doc, as_tree=True, utc_offset=8):
    if not comments_doc:
        return []
    comments = comments_doc.get('objects') or []
    for comment in comments:
        comment['author'] = get_comment_author_name(comment.get('author'), comment.get('email'))
        comment['avatar'] = get_comment_avatar(comment.get('email'))

        # 赋予 comment  id 的属性, 对 tree 的性质才有意义
        email = comment.get('email') or ''
        comment_date = comment.get('date') or ''
        origin_id = '%s %s' % (email, comment_date)
        comment['origin_id'] = origin_id
        comment['id'] = get_md5(origin_id)

        date = comment.get('date')
        if date and isinstance(date, string_types):

            try:
                date = utc_date_parse(date, utc_offset=utc_offset)
                comment['date'] = date
            except:
                pass

        if comment.get('reply'): # 回复于某个 comment
            comment['reply_to_id'] = get_md5(comment.get('reply'))

    # 处理为children
    if as_tree:
        raw_comments = comments
        comments_map = {}
        comments = []
        for comment in raw_comments:
            comments_map[comment.get('id')] = comment
        for comment in raw_comments:
            if comment.get('reply_to_id'):
                parent_id = comment.get('reply_to_id')
                parent_comment = comments_map.get(parent_id)
                if parent_comment:
                    parent_comment.setdefault('children', []).append(comment)
                    continue
            # 不隶属于某个父 comment 的
            comments.append(comment)

    return comments




