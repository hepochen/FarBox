# coding: utf8
import ujson as json
from flask import request
from geventwebsocket.exceptions import WebSocketError
from gevent import spawn, joinall
from farbox_bucket.settings import DEBUG
from farbox_bucket.utils import string_types
from farbox_bucket.settings import sentry_client
from farbox_bucket.utils.ssdb_utils import qpop_front, qpush_back
import logging

def push_message_to_ws(ws, message):
    # ws is websocket, 一个具体的连接
    if not isinstance(message, string_types):
        message = json.dumps(message)
    if not ws:
        return
    try:
        if 'HTTP_SEC_WEBSOCKET_KEY1' in ws.environ and 'HTTP_SEC_WEBSOCKET_KEY2' in ws.environ:
            # 针对旧版 websocket 的发送协议
            try:
                if isinstance(message, unicode):
                    message = message.encode('utf8')
                raw_socket = ws.stream.handler.socket
                message = "\x00" + message + "\xFF"
                raw_socket.sendall(message)
            except:
                if sentry_client:
                    sentry_client.captureException()
        else:
            ws.send(message)
    except WebSocketError:  # socket已经关闭，此时会触发on_close事件
        pass


def push_message_to_bucket(bucket, message):
    if not bucket:
        return
    # 实际上是
    data = dict(bucket=bucket, message=message)
    qpush_back('_realtime', data)




def do_push_message_to_buckets(clients, bucket_clients):
    records = qpop_front('_realtime', size=1000)
    push_jobs = []
    for record in records:
        bucket = record.get('bucket')
        message = record.get('message')
        if not bucket or not message:
            continue
        bucket_client_addresses = bucket_clients.get(bucket) or set()
        for bucket_client_address in bucket_client_addresses:
            client = clients.get(bucket_client_address)
            if not client:
                try: bucket_client_addresses.remove(client)
                except: pass
            else:
                push_job = spawn(push_message_to_ws, client.ws, message)
                logging.info('push event to %s:%s' % (bucket_client_address[0], bucket_client_address[1]))
                if DEBUG:
                    logging.info('%s' % message)
                push_jobs.append(push_job)
    if push_jobs:
        joinall(push_jobs, timeout=30 * 60)  # 30分钟后timeout




def get_bucket_ws_url(bucket):
    if DEBUG:
        ws_url = 'localhost:9080/bucket/%s' % bucket
    else:
        ws_url = '%s/_realtime/bucket/%s' % (request.host, bucket)
    return ws_url