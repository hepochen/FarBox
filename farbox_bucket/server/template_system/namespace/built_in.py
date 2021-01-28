# coding: utf8
from __future__ import absolute_import
import re

# 必须要有的一个系统公共函数

def set_property(parent, property_name, value):
    # 这个函数很重要，是在 jade 模板中被调用的，不能孔雀
    # 这里要隔绝 parent，不能传递特别的东西，不然会有安全隐患
    if hasattr(value, 'core'): # 可能某些 model 处理过的，比如Text
        value = value.core
    if parent is not None and isinstance(property_name, (str, unicode)) and re.match('[a-z_]\w*$', property_name, re.I):
        if isinstance(parent, dict): # 字典的处理
            parent[property_name] = value
        if getattr(parent, 'set_property_allowed', None) and not hasattr(value, '__call__'):
            # 不能赋函数值
            setattr(parent, property_name, value)
    return ''
