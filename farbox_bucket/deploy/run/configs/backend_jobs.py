#coding: utf8
from __future__ import absolute_import
import os
os.environ['GEVENT_RESOLVER'] = 'ares'
from gevent.monkey import patch_all; patch_all()
import gevent
import logging


from farbox_bucket.server.backend.backend_jobs import backend_jobs

if __name__ == '__main__':
    threads = []
    for job in backend_jobs:
        job = gevent.spawn(job)
        threads.append(job)

    logging.info('start cronjob now!')

    gevent.joinall(threads)
