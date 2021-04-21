#coding: utf8
from __future__ import absolute_import
import os
import socket
import uuid
from farbox_bucket.utils.ip.utils import get_current_ip, is_ipv4_ip
from farbox_bucket.utils.url import get_host_from_url
from farbox_bucket.utils.cache import cached
from farbox_bucket.utils.env import get_env

@cached
def get_current_node_id():
    # 获得当前服务器的 node_id，比如进行同步的时候，可以避免自己跟自己同步的死循环
    node_id_filepath = '/tmp/node_id.txt'
    try:
        with open(node_id_filepath, 'rb') as f:
            node_id_content = f.read().strip()
        if node_id_content:
            return node_id_content
    except:
        pass
    # at last， 构造并保存
    node_id = uuid.uuid4().hex
    try:
        with open(node_id_filepath, 'wb') as f:
            f.write(node_id)
    except:
        pass
    return node_id


def get_node_url(node, route='farbox_bucket_message_api'):
    node = node or ''
    if not node:
        node = os.environ.get('DEFAULT_NODE') or '127.0.0.1:7788'
    if '://' not in node:
        node = "http://%s" % (node.lstrip("/"))
    node_url = '%s/%s' % (node, route.lstrip('/'))
    return node_url



def get_node_ip(node):
    node_url = get_node_url(node)
    node_host = get_host_from_url(node_url)
    if node_host and ':' in node_host:
        node_host = node_host.split(':')[0]
    node_host = (node_host or '').strip().lower()
    if is_ipv4_ip(node_host):
        # 本身就是一个 ip
        return node_host
    else:
        try:
            ip = socket.gethostbyname(node_host)
        except:
            ip = '0.0.0.0'
        return ip




def get_remote_nodes_to_sync_from():
    # 从本地配置中，引入要同步的节点 list，每一行一条记录; 简单有效的是，每行一个 ip
    # 如果 node 本身没有 :<port> 的声明， 默认会认为是 :7788 端口
    nodes = []
    raw_content = get_env("server_sync_nodes") or ""
    lines = raw_content.split(',')
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            continue
        if not line:
            continue
        if ':' not in line:
            line = '%s:7788' % line
        nodes.append(line)
    return nodes

