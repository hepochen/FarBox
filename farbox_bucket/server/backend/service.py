#coding: utf8
import logging
import os
from farbox_bucket.utils.gevent_run import run_long_time, do_by_gevent_pool

def run_cmd(cmd):
    c_f = os.popen(cmd)
    try:
        return c_f.read().strip()
    except:
        return None


@run_long_time(wait=6*60*60, sleep_at_end=12*60*60, log='run logrotate')
def run_logrotate():
    if not os.path.isfile("/usr/sbin/logrotate"):
        return
    if not os.path.isfile("/etc/logrotate.d/farbox_bucket"):
        return
    run_cmd("/usr/sbin/logrotate /etc/logrotate.d/farbox_bucket")


@run_long_time(wait=10, sleep_at_end=2*60, log='keep watch nginx')
def keep_watch_nginx():
    cmd_result = run_cmd('ps -C nginx -o pid --no-headers')
    if not cmd_result:
        logging.info('try to start nginx')
        start_result = run_cmd("/etc/init.d/nginx start")
        logging.info(start_result)
    elif len(cmd_result.split())<2: # 只剩一个主进程了...
        logging.info('try to reload nginx')
        start_result = run_cmd("/usr/nginx/sbin/nginx -s reload")
        logging.info(start_result)
    else:
        #logging.info('the nginx is alive')
        pass


@run_long_time(wait=10, sleep_at_end=2*60, log='keep watch memcache')
def keep_watch_memcache():
    cmd_result = run_cmd('ps -C memcached -o pid --no-headers')
    if not cmd_result:
        logging.info('try to start memcached')
        start_result = run_cmd("/etc/init.d/memcached start")
        logging.info(start_result)
    else:
        pass



@run_long_time(wait=24*60*60, sleep_at_end=24*60*60, log='restart backend per day')
def restart_backend_per_day():
    run_cmd('/usr/local/bin/supervisorctl restart farbox_bucket_backend')


@run_long_time(wait=24*60*60, sleep_at_end=24*60*60, log='restart websocket server per day')
def restart_websocket_server_per_day():
    run_cmd('kill -HUP `cat /tmp/websocket_server.pid`')