#coding: utf8
from __future__ import absolute_import
import os
os.environ['GEVENT_RESOLVER'] = 'ares'
from gevent.monkey import patch_all; patch_all()
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

from geventwebsocket import WebSocketApplication
from geventwebsocket.exceptions import WebSocketError
from geventwebsocket import Resource

from gevent import spawn, spawn_later
import re, os
import ujson as json
from farbox_bucket.settings import sentry_client
from farbox_bucket.bucket.utils import has_bucket
from farbox_bucket.utils.memcache import get_cache_client

from .utils import do_push_message_to_buckets


ping_info = json.dumps(dict(type='ping'))

MAX_CONNECTIONS_PER_IP = 100


class WSApplication(WebSocketApplication):
    def __init__(self, *args, **kwargs):
        WebSocketApplication.__init__(self, *args, **kwargs)
        self.pid = os.getpid()
        self.cache_client =  get_cache_client()

    def get_bucket(self):
        # 得到当前请求的 room name
        if self.ws.path is None:
            return
        path = self.ws.path.rstrip('/')
        if re.search(r'/bucket/', path):
            bucket = path.split('/bucket/')[-1]
            if not has_bucket(bucket):
                bucket =  None
            return bucket
        else:
            return None

    def on_open(self):
        bucket = self.get_bucket()
        ip, port= self.ws.handler.client_address[:2]
        logging.info('%s:%s connect %s, pid:%s' % (ip, port, bucket, self.pid))
        if not bucket: # 不匹配的请求，关闭socket
            self.ws.close()
            return

        if ip!= '127.0.0.1': # 本地的无限制
            # 在300s 内，同一个 ip，最多建立 ws 连接
            connections_per_ip_count = self.cache_client.incr('%s:ws'%ip, 1, default_value=1, expiration=300)
            if connections_per_ip_count == MAX_CONNECTIONS_PER_IP:
                # = 的判断，主要是为了日志用的
                logging.info('%s more than %s connections in 5 mins, start to block it' % (ip, MAX_CONNECTIONS_PER_IP))
            if connections_per_ip_count > MAX_CONNECTIONS_PER_IP:
                # 5分钟之内，超过100次connect
                self.ws.close()
                return

        # add client add_ress
        server = self.ws.handler.server
        if not hasattr(server, 'bucket_clients'):
            server.bucket_clients = {}
        server.bucket_clients.setdefault(bucket, set())
        server.bucket_clients[bucket].add(self.ws.handler.client_address)




    def on_message(self, message, *args, **kwargs):
        if message == 'ping':
            pings_per_ip = self.cache_client.incr('%s:wsp' % str(self.ws.handler.client_address), 1, default_value=1, expiration=180)
            if pings_per_ip > 10: # 一个connection 3分钟内最多ping 10次
                self.ws.close()
            else:
                try:
                    self.ws.send(ping_info)
                except WebSocketError: # 无法send，是因为端口已经被关闭
                    pass
        elif message:# 不接受对方推送的信息
            self.ws.close()


    def on_close(self, reason):
        client_address = self.ws.handler.client_address
        bucket = self.get_bucket()
        if not bucket:
            return
        if not hasattr(self.ws.server, 'bucket_clients'):
            self.ws.server.bucket_clients = {}
        bucket_client_addresses = self.ws.server.bucket_clients.get(client_address) or set()
        try: bucket_client_addresses.remove(self.ws.handler.client_address)
        except: pass
        if not bucket_client_addresses:
            self.ws.server.bucket_clients.pop(client_address, None)



class WebSocketResource(Resource):
    def __init__(self, *args, **kwargs):
        Resource.__init__(self, *args, **kwargs)
        self.clients = {}
        self.bucket_clients = {}

        spawn(self.broadcast_forever)


    def broadcast_forever(self):
        try:
            do_push_message_to_buckets(self.clients, self.bucket_clients)
        except:
            if sentry_client:
                sentry_client.captureException()
            logging.error('push_events failed')
        spawn_later(1, self.broadcast_forever) # 1s后loop


    def __call__(self, environ, start_response):
        environ = environ
        current_app = self._app_by_path(environ['PATH_INFO'])
        # clients = handler.server.clients
        # client_address = handler.client_address # 要重新获取X-Real-IP/port作为值，有可能是unix过来的
        if 'wsgi.websocket' in environ:
            ws = environ['wsgi.websocket']
            self.clients = ws.handler.server.clients
            if not hasattr(ws.handler.server, 'bucket_clients'):
                ws.handler.server.bucket_clients = {}
            self.bucket_clients = ws.handler.server.bucket_clients
            current_app = current_app(ws)
            current_app.ws = ws
            current_app.handle()
            return None
        else:
            data = "this is Realtime API Page, you should request by WebSocket\n"
            start_response("200 OK", [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(data)))
            ])
            return iter([data])





# app是多个WebSocketApplication的混合，通过url自动匹配
# re.match(path, environ['PATH_INFO'])

# worker: geventwebsocket.gunicorn.workers.GeventWebSocketWorker
# 其会定义 handler wsgi_handler = WebSocketHandler

# 一个handler，一般是运行start_response

# WSGIHandler中
# handle -> self.handle_one_request() ->  handle_one_response  (一般会调用)-> run_application --> self.result = self.application(self.environ, self.start_response)
# 最后的application，实际上就是我们自己的main app，比如下面WebSocketApp的实例化对象，相当于主要__call__(env, start_response)

app = WebSocketResource({
    '/': WSApplication,
})