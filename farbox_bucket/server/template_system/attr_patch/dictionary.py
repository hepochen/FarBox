# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import get_value_from_data, smart_unicode
from farbox_bucket.bucket.utils import get_bucket_in_request_context, get_bucket_site_configs
from farbox_bucket.bucket.record.get.folder import get_folder_children_count
from farbox_bucket.bucket.record.utils import get_type_from_record
from farbox_bucket.server.statistics.post_visits import get_post_visits_count
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.server.template_system.model.category import get_record_parent_category
from farbox_bucket.server.template_system.namespace.data import get_data
from farbox_bucket.server.utils.doc_url import get_doc_url

def set(obj, key, value):
    obj[key] = value
    return ''


def visits(obj):
    value = get_post_visits_count(obj, 'visits')
    obj['visits'] = value
    return value


def visitors(obj):
    value = get_post_visits_count(obj, 'visitors')
    obj['visitors'] = value
    return value



def comments(obj):
    from farbox_bucket.server.comments.utils import get_comments
    cmts = get_comments(obj) or []
    obj['comments'] = cmts
    return cmts


def comments_count(obj):
    value = len(comments(obj))
    obj['comments_count'] = value
    return value


def images_count(obj):
    if get_type_from_record(obj) == "folder":
        bucket = get_bucket_in_request_context()
        return get_folder_children_count(bucket, obj.get("path"), field="images")
    return 0


def posts_count(obj):
    if get_type_from_record(obj) == "folder":
        bucket = get_bucket_in_request_context()
        return get_folder_children_count(bucket, obj.get("path"), field="posts")
    return 0


def __type(obj):
    return get_type_from_record(obj)


def cover(obj):
    if get_type_from_record(obj) == "folder":
        bucket = get_bucket_in_request_context()
        path = obj.get("path")
        if bucket and path:
            result = get_data(type="image", path=path, level=1, limit=1, sort="-date")
            if result:
                return get_doc_url(result[0])
    return ""


def url(obj):
    return get_doc_url(obj)


def comments_as_html(obj):
    doc = obj
    site_configs = get_bucket_site_configs()
    should_hide_comments = not get_value_from_data(site_configs, 'comments', True)
    third_party_comments_script = get_value_from_data(site_configs, 'third_party_comments_script') or ''
    third_party_comments_script = smart_unicode(third_party_comments_script.strip())
    if third_party_comments_script:  # 有第三方评论脚本，直接进行替换
        should_hide_comments = True

    if not should_hide_comments and get_value_from_data(doc, 'metadata.comment') in [False, 'no', 'No']:
        # doc 本身不允许显示
        should_hide_comments = True

    if should_hide_comments:  # 不显示评论系统
        return third_party_comments_script

    html = render_api_template('comments.jade', doc=doc)
    return html


def get_comments_people(obj, prefix='@'):
    from farbox_bucket.server.comments.contacts import get_all_contacts_from_post
    if not obj:
        return []
    doc_type = obj.get('_type')
    if doc_type not in ['post']:
        return []
    people = []
    cmts = comments(obj)
    contacts = get_all_contacts_from_post(obj, comments=cmts)
    for person in contacts.keys():
        people.append('%s%s'%(prefix, person))
    return people


def category(obj):
    c = get_record_parent_category(obj)
    obj['category'] = c
    return c
