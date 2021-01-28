#coding: utf8
from __future__ import absolute_import
from flask import request
import time

def time_cost_handler(response=None):
    if not response: # before request
        request.environ['request_at'] = time.time()
    else: # after request
        request_at = request.environ.get('request_at')
        if request_at:
            time_cost = time.time() - request_at
            response.headers['x-render-time'] = str(time_cost) # 渲染消耗的时间，单位秒
        return response
