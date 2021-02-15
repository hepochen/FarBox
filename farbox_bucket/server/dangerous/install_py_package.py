# coding: utf8
import os
import re
from gevent import spawn_later


def restart_web_service():
    try:
        with os.popen("kill -HUP `cat /tmp/web_server.pid`") as f:
            f.read()
    except:
        pass

def install_py_package_by_web(url):
    if not "://" in url:
        return
    # https://files.pythonhosted.org/packages/57/43/8d7120e714fbaa6d44ab381333f8b3a2960f2bdfebe3091c68c42d89ee14/farbox_bucket-0.1880.tar.gz
    if not re.match("[:/a-z0-9\-_.]+$", url):
        return "this url is invalid"
    try:
        with os.popen("pip install %s" % url) as f:
            result = f.read()
    except:
        result = ""
    spawn_later(3, restart_web_service)
    return result



