#coding:utf8
import os
os.environ['GEVENT_RESOLVER'] = 'ares'
import multiprocessing

try:
    import psutil as pu
except:
    pu = None

cpu_cores = multiprocessing.cpu_count()
if cpu_cores >=8 :
    workers = cpu_cores
else:
    workers = cpu_cores*2 + 1
if workers > 11:
    workers = 11 # max workers

if pu:
    mem_info = pu.virtual_memory()
    if mem_info.total < 5*1024*1024*1024: # 5G以下
        workers = 2

bind = "unix:/tmp/web_server.sock"
daemon = False
worker_class = 'gevent'
worker_connections = 1000 # worker的并发数，1k为默认值
max_requests = 6000
#preload = True
timeout = 30
graceful_timeout = 30
pidfile = '/tmp/web_server.pid'
proc_name = 'fb_bucket'

limit_request_line = 6500
# in bytes just 0.5k #目前并没有什么大的数据上的交互,但会影响url的长度限制
# updated 201-3-20 支付宝这边回调的URL有点长 1300+

# timeout 固定多少时间重启worker
# graceful_timeout 接到重启后，多少时间后重启