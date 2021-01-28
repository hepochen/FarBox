# coding: utf8
from __future__ import absolute_import
from flask import g
from farbox_bucket.utils import get_value_from_data, smart_unicode
from farbox_bucket.server.statistics.post_visits import get_post_visits_count
from farbox_bucket.server.comments.utils import get_comments
from farbox_bucket.server.comments.contacts import get_all_contacts_from_post
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.server.template_system.model.category import get_record_parent_category

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
    cmts = get_comments(obj) or []
    obj['comments'] = cmts
    return cmts


def comments_count(obj):
    value = len(comments(obj))
    obj['comments_count'] = value
    return value



def comments_as_html(obj):
    doc = obj
    should_hide_comments = not get_value_from_data(g, 'site.comments', True)
    third_party_comments_script = get_value_from_data(g, 'site.third_party_comments_script') or ''
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
