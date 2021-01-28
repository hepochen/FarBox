# coding: utf8
import os

def try_to_reload_web_app():
    if not os.path.isfile("/tmp/web_server.pid"):
        return
    c_f = os.popen("kill -HUP `cat /tmp/web_server.pid`")
    try:
        c_f.read()
    except:
        pass