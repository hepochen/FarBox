#coding: utf8
from __future__ import absolute_import
from farbox_bucket.server.backend.sync.buckets import sync_buckets_from_remote_marked, sync_buckets_from_remote_nodes
from farbox_bucket.server.backend.service import keep_watch_nginx, restart_backend_per_day, keep_watch_memcache, restart_websocket_server_per_day

from farbox_bucket.server.backend.status.server_status import report_server_status


backend_jobs = [
    sync_buckets_from_remote_marked,
    sync_buckets_from_remote_nodes,
    keep_watch_nginx,
    keep_watch_memcache,
    restart_backend_per_day,
    report_server_status,
    restart_websocket_server_per_day,
]