# coding: utf8
# 不能把app变量放到这里来，因为app本身会开启一些loop的命令，会导致其它地方调用websocket_server.xxx下的utils，会强启app内的命令