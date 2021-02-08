#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.env import get_env
from farbox_bucket.server.backend.service import keep_watch_nginx, restart_backend_per_day, keep_watch_memcache, run_logrotate

should_sync_buckets = get_env("should_sync_buckets_in_backend")
if should_sync_buckets == "no":
    should_sync_buckets = False

backend_jobs = [
    keep_watch_nginx,
    keep_watch_memcache,
    restart_backend_per_day,
    run_logrotate,
]

if should_sync_buckets:
    # 减少 backend 的内存占用，如果只是守护性质的话
    from farbox_bucket.server.backend.sync.buckets import sync_buckets_from_remote_marked, sync_buckets_from_remote_nodes
    backend_jobs.append(sync_buckets_from_remote_marked)
    backend_jobs.append(sync_buckets_from_remote_nodes)