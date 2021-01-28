#coding:utf8
import os
os.environ['GEVENT_RESOLVER'] = 'ares'
workers = 1
bind = "unix:/tmp/websocket_server.sock"
daemon = False
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'
#worker_connections = 1000
#max_requests = 5000 #默认为0，不然worker会被重启
keepalive = 5
timeout = 300
graceful_timeout = 30
pidfile = '/tmp/websocket_server.pid'
limit_request_line = 500 #in bytes just 0.5k #目前并没有什么大的数据上的交互,但会影响url的长度限制
proc_name = 'websocket'
# timeout 固定多少时间重启worker
# graceful_timeout 接到重启后，多少时间后重启





