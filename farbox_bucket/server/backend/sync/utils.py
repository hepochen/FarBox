#coding: utf8
from __future__ import absolute_import
import os


def get_node_url(node, route='farbox_bucket_message_api'):
    node = node or ''
    if '://' in node:
        node = node.split('://')[-1]
    node = node.strip().strip('/').strip()
    if not node:
        node = os.environ.get('DEFAULT_NODE') or '127.0.0.1:7788'
    if ':' not in node:
        node = '%s:7788' % node
    node_url = 'http://%s/%s' % (node, route.lstrip('/'))
    return node_url