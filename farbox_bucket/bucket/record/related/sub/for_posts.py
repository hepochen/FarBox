# coding: utf8
import time, os
from farbox_bucket.utils import to_int, smart_unicode, is_a_markdown_file
from farbox_bucket.bucket.utils import get_bucket_posts_info, set_bucket_configs, get_bucket_name_for_path
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.utils.md_related.markdown_doc_links import get_linked_docs_from_markdown_content


# for Markdown document only
# 服务器端每次 path 相关的 record 过来，会更新，但同时，也允许 client 直接覆盖性更新这部分数据
# 支持双向连接的语法
def update_post_tags_words_info(bucket, record_data):
    path = get_path_from_record(record_data)
    lower_path = path.lower().lstrip('/')
    if not path:
        return
    if not is_a_markdown_file(path):
        return
    if lower_path.startswith('_nav/'):
        return
    posts_info = get_bucket_posts_info(bucket) or {}
    # data init
    bucket_text_words = to_int(posts_info.get('text_words') or 0, default_if_fail=0)

    # prepare tags info
    tags_info = posts_info.setdefault('tags', {})  # {'paths':{path:[tag1,tag2]} ,  'tags': {'tag':[path1, path2]} }
    tags_info_tags = tags_info.setdefault('tags', {})
    tags_info_paths = tags_info.setdefault('paths', {})

    # prepare links info
    links_info = posts_info.setdefault("links", {}) # {'paths': {path:[back_path1, back_path2]]} ,
                                                    #   'back_paths': {'back_path':[path1, path2]} }
    links_info_links = links_info.setdefault("links", {})
    links_info_paths = links_info.setdefault("paths", {})

    words_info = posts_info.setdefault('words', {})  # {'path': text_words}

    is_deleted = record_data.get('is_deleted', False)
    post_status = record_data.get('status') or 'public'
    post_tags = record_data.get('tags') or []
    if not isinstance(post_tags, (list, tuple)):
        post_tags = []

    post_doc_links, wiki_tags = get_linked_docs_from_markdown_content(path, record_data.get("raw_content"))
    if not isinstance(post_doc_links, (list, tuple)):
        post_doc_links = []

    text_words = to_int(record_data.get('text_words'), default_if_fail=0)

    # 如果已有 words 的信息，先减去，避免重复计算
    old_text_words = to_int(words_info.get(lower_path), default_if_fail=0)
    if old_text_words:
        bucket_text_words -= old_text_words

    # deleted, 草稿类似的状态，不进入计算；去除相关的信息
    if is_deleted or post_status in ['draft', 'private']:
        words_info.pop(lower_path, None)

        # handle delete tags
        old_tags = tags_info_paths.get(lower_path)
        if not isinstance(old_tags, (list, tuple)):
            old_tags = []
        old_tags = [smart_unicode(tag) for tag in old_tags]
        tags_info_paths.pop(lower_path, None)
        for tag in old_tags:
            tags_info_tags_for_tag_paths = tags_info_tags.setdefault(tag, [])
            if lower_path in tags_info_tags_for_tag_paths:
                tags_info_tags_for_tag_paths.remove(lower_path)
                if not tags_info_tags_for_tag_paths: # 空的 tags
                    tags_info_tags.pop(tag, None)

        # handle delete links
        old_links = links_info_paths.get(lower_path)
        if not isinstance(old_links, (list, tuple)):
            old_links = []
        old_links = [smart_unicode(link) for link in old_links]
        links_info_paths.pop(lower_path, None)
        for link in old_links:
            links_info_link_back_paths = links_info_links.setdefault(link, [])
            if lower_path in links_info_link_back_paths:
                links_info_link_back_paths.remove(lower_path)
                if not links_info_link_back_paths: # 空的 links 了
                    links_info_links.pop(link, None)


    else:
        bucket_text_words += text_words
        words_info[lower_path] = text_words

        # handle tags
        if post_tags:
            tags_info_paths[lower_path] = post_tags
        for tag in post_tags:
            tags_info_tags_for_tag_paths = tags_info_tags.setdefault(tag, [])
            if lower_path not in tags_info_tags_for_tag_paths:
                tags_info_tags_for_tag_paths.append(lower_path)
        empty_tags = []
        for tag, paths_tagged in tags_info_tags.items():
            if not paths_tagged:
                empty_tags.append(tag)
                continue
            if not isinstance(paths_tagged, list):
                continue
            if lower_path in paths_tagged and tag not in post_tags:
                paths_tagged.remove(lower_path)
            if not paths_tagged:
                empty_tags.append(tag)
        for empty_tag in empty_tags:
            tags_info_tags.pop(empty_tag, None)

        # handle links
        if post_doc_links:
            links_info_paths[lower_path] = post_doc_links
        for link in post_doc_links:
            links_info_link_back_paths = links_info_links.setdefault(link, [])
            if lower_path not in links_info_link_back_paths:
                links_info_link_back_paths.append(lower_path)
        empty_links = []
        for link, paths_linked in links_info_links.items():
            if not paths_linked:
                empty_links.append(link)
                continue
            if not isinstance(paths_linked, list):
                continue
            if lower_path in paths_linked and link not in post_doc_links:
                paths_linked.remove(lower_path)
            if not paths_linked:
                empty_links.append(link)
        for empty_link in empty_links:
            links_info_links.pop(empty_link, None)

    if bucket_text_words < 0:
        bucket_text_words = 0

    posts_info['text_words'] = bucket_text_words

    set_bucket_configs(bucket, configs=posts_info, config_type='posts')

    #return posts_info

