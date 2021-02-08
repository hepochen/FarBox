# coding: utf8
import os
from .log_rotate import install_project_log_rotate

def try_to_reload_web_app(restart_backend=False):
    install_project_log_rotate(force=True)
    if not os.path.isfile("/tmp/web_server.pid"):
        return
    try:
        with os.popen("kill -HUP `cat /tmp/web_server.pid`") as f:
            f.read()
    except:
        pass

    if restart_backend:
        try:
            with os.popen("/usr/local/bin/supervisorctl restart farbox_bucket_backend") as f:
                f.read()
        except:
            pass