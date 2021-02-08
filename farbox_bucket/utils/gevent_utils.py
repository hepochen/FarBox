# coding: utf8
from __future__ import absolute_import
from gevent.hub import Hub
import gc, gevent
from gevent import spawn
from gevent.greenlet import Greenlet
from gevent.pool import Pool
from gevent.timeout import Timeout

IGNORE_ERROR = Hub.SYSTEM_ERROR + Hub.NOT_ERROR


def register_error_handler(error_handler):

    Hub._origin_handle_error = Hub.handle_error

    def custom_handle_error(self, context, type, value, tb):
        if not issubclass(type, IGNORE_ERROR):
            # print 'Got error from greenlet:', context, type, value, tb
            error_handler(context, (type, value, tb))

        self._origin_handle_error(context, type, value, tb)

    Hub.handle_error = custom_handle_error


def gevent_error_sent_by_sentry(sentry_client):
    def gevent_error_handler(context, exc_info):
        """Here goes your custom error handling logics"""
        e = exc_info[1]
        try:
            sentry_client.captureException(exc_info=exc_info)
        except:
            # 避免捕获过程中的死循环问题
            pass
    register_error_handler(gevent_error_handler)


def get_all_gevent_jobs():
    jobs = []
    for ob in gc.get_objects():
        if isinstance(ob, Greenlet) and ob:
            if ob.dead:
                continue
            if hasattr(ob, 'ready') and ob.ready():
                continue
            jobs.append(ob)
    return jobs

def wait_all_gevent_jobs_finished():
    # 等待所有gevent的job完成，并且最终删除这个对应的job，因为不需要了
    jobs = get_all_gevent_jobs()
    gevent.joinall(jobs)
    for job in jobs:
        try: del job
        except: pass



def do_by_gevent_pool(pool_size=100, job_func=None, loop_items=None, timeout=None, wait_timeout=5*60, **kwargs):
    if not job_func or not loop_items:
        return
    worker_pool = Pool(pool_size)
    if hasattr(loop_items, '__call__'):
        for item in loop_items():
            while worker_pool.full():
                try:
                    worker_pool.wait_available(timeout=wait_timeout)
                except Timeout:
                    worker_pool.kill()
            worker_pool.spawn(job_func, item, **kwargs)
    else:
        for item in loop_items:
            while worker_pool.full():
                try:
                    worker_pool.wait_available(timeout=wait_timeout)
                except Timeout:
                    worker_pool.kill()
            worker_pool.spawn(job_func, item, **kwargs)
    try:
        worker_pool.join(timeout=timeout)
        return True # 表示处理完成
    except:
        return False



def greenlet_quiet_error_handler(greenlet):
    pass


def get_result_by_gevent_with_timeout_block(function, timeout, fallback_function=None, auto_kill=False, raise_error=True):
    g_job = spawn(function)
    if not raise_error:
        g_job.link_exception(greenlet_quiet_error_handler)
    try:
        result = g_job.get(block=True, timeout=timeout)
        return result
    except Timeout:
        if auto_kill:
            g_job.kill(block=False)
        if fallback_function:
            result = fallback_function()
        else:
            result = None
        return result

