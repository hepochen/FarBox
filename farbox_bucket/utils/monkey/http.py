#coding: utf8
from httplib import HTTPConnection
from urllib3 import PoolManager

_get_response = HTTPConnection.getresponse
_pool_manager_init = PoolManager.__init__

def http_connection_get_response(self, buffering=False):
    response = _get_response(self, buffering)
    if response.status == 206: # 不是200, 像Dropbox的API就会报错
        response.status = 200
    return response


def pool_manger_init(self, num_pools=10, headers=None, **connection_pool_kw):
    connection_pool_kw['block'] = True
    connection_pool_kw['maxsize'] = 500
    _pool_manager_init(self, num_pools, headers, **connection_pool_kw)


PoolManager.__init__ = pool_manger_init
HTTPConnection.getresponse = http_connection_get_response
