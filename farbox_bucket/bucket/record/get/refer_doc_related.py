# coding: utf8
from farbox_bucket.utils import smart_unicode, to_int, sort_objects_by
from farbox_bucket.bucket.utils import get_bucket_posts_info
from .path_related import get_record_by_path, get_records_by_paths


def get_links_info(bucket):
    # k:v --> tag: [path1, path2]
    posts = get_bucket_posts_info(bucket) or {}
    raw_info = posts.get('links') or {} # links.links
    if not isinstance(raw_info, dict):
        raw_info = {}
    info = raw_info.get('links') or {}
    if not isinstance(info, dict):
        info = {}
    return info

def get_links_paths_info(bucket):
    # k:v --> tag: [path1, path2]
    posts = get_bucket_posts_info(bucket) or {}
    raw_info = posts.get('links') or {} # links.links
    if not isinstance(raw_info, dict):
        raw_info = {}
    info = raw_info.get('paths') or {}
    if not isinstance(info, dict):
        info = {}
    return info


def get_records_by_post_path_back_referred(bucket, post_path, sort_by='-date'):
    # post_path 的 back-link-docs
    if not bucket:
        return []
    if not post_path:
        return []
    links_info = get_links_info(bucket)
    paths = []
    if isinstance(post_path, (list, tuple)): # tag 如果是 list 传入，是 OR 的查询逻辑
        post_paths = post_path
        for post_path in post_paths:
            if not post_path: continue
            post_path = smart_unicode(post_path).strip()
            matched_paths = links_info.get(post_path) or []
            for path in matched_paths:
                if path not in paths: paths.append(path)
    else:
        post_path = smart_unicode(post_path).strip()
        paths = links_info.get(post_path) or []
    if not paths:
        return []
    records = get_records_by_paths(bucket, paths, limit=500)
    records = sort_objects_by(records, attr=sort_by)
    return records


def get_records_by_post_path_referred(bucket, post_path, sort_by='-date'):
    if not bucket:
        return []
    if not post_path:
        return []
    links_info = get_links_paths_info(bucket)
    paths = []
    if isinstance(post_path, (list, tuple)):  # tag 如果是 list 传入，是 OR 的查询逻辑
        post_paths = post_path
        for post_path in post_paths:
            if not post_path: continue
            post_path = smart_unicode(post_path).strip()
            matched_paths = links_info.get(post_path) or []
            for path in matched_paths:
                if path not in paths: paths.append(path)
    else:
        post_path = smart_unicode(post_path).strip()
        paths = links_info.get(post_path) or []
    if not paths:
        return []
    records = get_records_by_paths(bucket, paths, limit=500)
    records = sort_objects_by(records, attr=sort_by)
    return records
