#coding: utf8
import random
from farbox_bucket.utils import smart_str
import socket, time, zlib
import hashlib
import logging
import os
from pymemcache.client.base import Client as MemcacheClient
from pymemcache.exceptions import MemcacheError


try:
    import telnetlib
except:
    telnetlib = None


def get_all_memcached_keys(host='127.0.0.1', port=11211):
    if not telnetlib:
        return []
    t = telnetlib.Telnet(host, port)
    t.write('stats items STAT items:0:number 0 END\n')
    items = t.read_until('END').split('\r\n')
    keys = set()
    for item in items:
        parts = item.split(':')
        if not len(parts) >= 3:
            continue
        slab = parts[1]
        t.write('stats cachedump {} 200000 ITEM views.decorators.cache.cache_header..cc7d9 [6 b; 1256056128 s] END\n'.format(slab))
        cachelines = t.read_until('END').split('\r\n')
        for line in cachelines:
            parts = line.split(' ')
            if not len(parts) >= 3:
                continue
            keys.add(parts[1])
    t.close()
    return list(keys)


class Client(object):
    def __init__(self, host='127.0.0.1:11211', max_connections=100):
        self.host_ip, self.host_port = host.split(':', 1)
        self.host_port = int(self.host_port)

        self.host = (self.host_ip, self.host_port)
        #self.host = host

        self.max_connections = max_connections
        self.clients = []
        self.service_stopped = False
        self.last_connect_at = None

    def get_all_keys(self):
        return get_all_memcached_keys(self.host_ip, self.host_port)


    def create_client(self, try_re_connect=True):
        try:
            client = MemcacheClient(self.host)
            #client.connect()
            self.clients.append(client)
            return client
        except socket.error, e:
            message = getattr(e, 'message', '') or getattr(e, 'strerror', '')
            if 'refused' in message:
                if try_re_connect:
                    self.re_connect()
                return None
        except MemcacheError:
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

    def safe_try(self, client, func_name, *args, **kwargs):
        if self.service_stopped:
            return None

        # 在client不存在，或者连接出错的情况下，也能安全的运行
        if not client:
            return None
        func = getattr(client, func_name) # 比如client.get 要走memcache的socket
        func_kwargs = kwargs.copy()
        func_kwargs.pop('tried_times', None) # 这个参数，不参与func上的运行
        try:
            return func(*args, **func_kwargs)
        except AssertionError, e: # 当前的client在另外的协程中被使用了，重试，但最多不超过10次
            tried_times = kwargs.pop('tried_times', 1) # 尝试次数
            if tried_times > 10: #
                return None
            else:
                kwargs['tried_times'] = tried_times+1
                return self.safe_try(client, func_name, *args, **kwargs)
        except (MemcacheError, socket.error, IOError), e:
            if isinstance(e, socket.error) and 'refused' in e.message:
                # 很有可能memcache的服务已经停止了
                self.re_connect()
                return None

            if 'reset by peer' in e.message or isinstance(e, IOError):
                try:
                    self.clients.remove(client)
                except ValueError: # client不在clients中
                    pass
                client = self.create_client()
                if not client:
                    return None
                try:
                    func = getattr(client, func_name)
                    return func(*args, **func_kwargs)
                except (MemcacheError, socket.error):
                    logging.error('MemcachedError or memcache socket error')

    def stats(self):
        return self.safe_try(self.current_client, 'stats')

    def set(self, key, data, expiration=0, zipped=False, hash_key=False, *args, **kwargs):
        if not isinstance(key, str):
            key = smart_str(key)
        if not isinstance(data, str):
            data = smart_str(data)
        if zipped: # 需要压缩的 # compress的效率很高，1亿字节大概5秒, 压缩率接近50%
            try:
                data = zlib.compress(data)
            except:
                pass
        if hash_key:
            key = hashlib.md5(key).hexdigest()
        expiration = int(expiration)
        self.safe_try(self.current_client, 'set', key, data, expiration, *args, **kwargs)

    def delete(self, key, hashed=False):
        if hashed:
            key = hashlib.md5(key).hexdigest()
        self.safe_try(self.current_client, 'delete', key)

    def incr(self, key, value=1, default_value=1, expiration=0):
        # expiration的周期不会被改变
        value = self.safe_try(self.current_client, 'incr', key, value)
        if value and value.isdigit():
            return int(value)
        elif value: # NOT_FOUND
            self.set(key, default_value, expiration=expiration) #
            return default_value
        else:
            return default_value

    def decr(self, key, value=1, default_value=1, expiration=0):
        value = self.safe_try(self.current_client, 'decr', key, value)
        if value and value.isdigit():
            return int(value)
        elif value: # NOT_FOUND
            self.set(key, default_value, expiration=expiration) #
            return default_value
        else:
            return default_value

    def get(self, key, default=None, zipped=False, hash_key=False):
        if not isinstance(key, str):
            key = smart_str(key)
        if hash_key:
            key = hashlib.md5(key).hexdigest()
        if not key:
            return None
        data = self.safe_try(self.current_client, 'get', key)
        if data is None:
            return default
        if isinstance(data, (tuple, list)):
            data = data[0]
        if zipped:
            try:
                data = zlib.decompress(data)
            except:
                return None
        return data

    def auto_cache(self, key, data_func, zipped=False, expiration=0):
        cached = self.get(key, zipped=zipped)
        if cached:
            return cached
        else:
            data = data_func()
            self.set(key, data, expiration=expiration, zipped=zipped)
            return data

    def __getattr__(self, item):
        return getattr(self.current_client, item)



mem_cache_client = None

def get_cache_client():
    global mem_cache_client
    if mem_cache_client is not None:
        return mem_cache_client
    max_connections = os.environ.get('MEMCACHE_CONNECTIONS')
    if max_connections:
        try:
            max_connections = int(max_connections)
        except:
            pass
    if not max_connections:
        max_connections = 100
    mem_cache_client = Client(max_connections=max_connections)
    return mem_cache_client


cache_client = get_cache_client()