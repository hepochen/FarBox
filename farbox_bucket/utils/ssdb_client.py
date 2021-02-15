# coding: utf8
import pyssdb
import socket
import random
import time


class SSDB_Client(object):
    def __init__(self, host='127.0.0.1', port=8888, max_connections=5):
        self.max_connections = max_connections
        self.host = host
        self.port = port
        self.clients = []
        self.service_stopped = False
        self.last_connect_at = None

        self.re_connect()


    def __nonzero__(self):
        if not self.clients:
            self.re_connect()
            return False
        else:
            return True

    def create_client(self, try_re_connect=True):
        try:
            client = pyssdb.Client(self.host, self.port)
            #client.connect()
            self.clients.append(client)
            return client
        except socket.error as e:
            message = getattr(e, 'message', '') or getattr(e, 'strerror', '')
            if 'refused' in message:
                if try_re_connect:
                    self.re_connect()
                return None
        except:
            return None

    @property
    def current_client(self):
        if not self.clients:
            self.create_client()
        elif len(self.clients) < self.max_connections:
            self.create_client()
        if not self.clients:
            return None
        else:
            return random.choice(self.clients)

    def re_connect(self):
        now = time.time()
        if self.last_connect_at and (now-self.last_connect_at) < 10:
            # 10秒内已经重新连接尝试了，ignore
            return

        self.service_stopped = True
        new_client = self.create_client(try_re_connect=False)
        self.last_connect_at = now
        if new_client:
            self.service_stopped = False


    def __getattr__(self, item):
        client = self.current_client
        if not client:
            raise AttributeError("ssdb is not valid? can not handle attribute for %s" % item)
        else:
            return getattr(client, item)