#coding: utf8
from __future__ import absolute_import, print_function
import datetime
from farbox_bucket.utils import smart_str, string_types
from farbox_bucket.utils.path import write_file
from .sync_utils import  make_sure_sync_log_path



def write_logs(logs, app_name, filepath=None, root=None,):
    # filepath: logs for which file, root: under which root
    if isinstance(logs, string_types):
        logs = [logs]
    if not logs:
        return # ignore
    if not root:
        return # ignore
    now = datetime.datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    log_path = make_sure_sync_log_path(root, app_name)
    with open(log_path, 'a') as f:
        for log in logs:
            log = raw_log = smart_str(log)
            if filepath:
                filepath = smart_str(filepath)
                log = '%s: %s %s\n' %(now_str, filepath, log)
            else:
                log = '%s %s\n' %(now_str, smart_str(log))
            write_file(f, log)

