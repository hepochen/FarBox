# coding: utf8

from farbox_bucket.utils import smart_unicode, to_int, sort_objects_by
from farbox_bucket.bucket.utils import get_bucket_posts_info
from .path_related import get_record_by_path, get_records_by_paths

def get_tags_info(bucket):
    # k:v --> tag: [path1, path2]
    posts = get_bucket_posts_info(bucket) or {}
    raw_info = posts.get('tags') or {}
    if not isinstance(raw_info, dict):
        raw_info = {}
    info = raw_info.get('tags') or {}
    if not isinstance(info, dict):
        info = {}
    return info


def get_records_by_tag(bucket, tag, sort_by='-date'):
    if not bucket:
        return []
    if not tag:
        return []
    tags_info = get_tags_info(bucket)
    if isinstance(tag, (list, tuple)): # tag 如果是 list 传入，是 OR 的查询逻辑
        paths = []
        tags = tag
        for tag in tags:
            if not tag: continue
            tag = smart_unicode(tag).strip()
            tag_matched_paths = tags_info.get(tag) or []
            for path in tag_matched_paths:
                if path not in paths: paths.append(path)
    else:
        tag = smart_unicode(tag)
        paths =  tags_info.get(tag) or []
    if not paths:
        return []
    records = get_records_by_paths(bucket, paths, limit=500)
    records = sort_objects_by(records, attr=sort_by)
    return records




