#coding: utf8
from __future__ import absolute_import
import gevent
import datetime
from gevent.pool import Pool
from gevent.timeout import Timeout
from functools import partial
from farbox_bucket.utils.logger import get_file_logger



def _run_long_time(func, wait=0, sleep_at_start=0, sleep_at_end=30*60, log=''):
    logger = get_file_logger('gevent_run')
    if sleep_at_end < 30:
        sleep_at_end = 30 # 最最最起码要有 30s 的间隔，不然就成死循环了
    def _func():
        if wait: # 任务启动时候的等待
            gevent.sleep(wait)
        while True:
            if sleep_at_start: # 头部休眠
                gevent.sleep(sleep_at_start)
            logger.info('%s, %s starting...'% (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log))
            try:
                func()
            except: # 避免异常，产生的卡顿问题
                logger.info('%s, %s failed'% (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log))
            logger.info('%s, %s ended'% (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), log))
            gevent.sleep(sleep_at_end)
    return _func



def run_long_time(*args, **kwargs):
    if len(args)==1 and not kwargs and hasattr(args[0], '__call__'):
        func = args[0]
        return _run_long_time(func)
    else:
        return partial(_run_long_time, *args, **kwargs)





def do_by_gevent_pool(pool_size=100, job_func=None, loop_items=None, timeout=None, wait_timeout=5*60, callback_func=None, **kwargs):
    if not job_func or not loop_items:
        return
    worker_pool = Pool(pool_size)
    for item in loop_items:
        while worker_pool.full():
            try:
                worker_pool.wait_available(timeout=wait_timeout)
            except Timeout:
                worker_pool.kill()
        worker_pool.spawn(job_func, item, **kwargs)
    try:
        worker_pool.join(timeout=timeout)
        if callback_func and hasattr(callback_func, "__call__"):
            try:callback_func()
            except: pass
        return True # 表示处理完成
    except:
        return False