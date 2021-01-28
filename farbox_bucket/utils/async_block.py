# coding: utf8
from __future__ import absolute_import
from flask import request
from gevent.event import Event
import gevent


async_website_blocks = {}


def run_in_website_with_block(func):
    def _func(*args, **kwargs):
        host = request.host
        block_event = async_website_blocks.setdefault(host, Event())
        while block_event.is_set():
            gevent.sleep(0.01)
        block_event.set()
        try:
            result = func(*args, **kwargs)
            block_event.clear()
            return result
        except Exception as e:
            block_event.clear()
            raise e
    return _func
