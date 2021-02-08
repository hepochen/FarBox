#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import smart_unicode, get_md5, string_types
from farbox_bucket.utils.functional import curry
from flask import _request_ctx_stack, request


# treat request as g

class G(object):
    pass

local_g = None
def get_g():
    global local_g
    if not _request_ctx_stack.top:
        # 不是以 app 的形式运行的，可能只是模板的调用
        local_g = local_g or G()
        return local_g
    else:
        return request

def cache_wrapper(func, cache_name):
    # 为了避免冲突，一般cache_name是以'cached_'开头的
    def _func(*args, **kwargs): #the real func
        g = get_g()
        if cache_name == 'no_cache': # 不对结果缓存
            return func(*args, **kwargs)

        # 获得/创建容器
        if not hasattr(g, cache_name):
            setattr(g,  cache_name, {})

        # 准备key值，可以在容器内进行匹配
        values = list(args) + kwargs.keys() + kwargs.values()
        key_list = []
        for value in values:
            if isinstance(value, dict) and '_id' in value:
                key_list.append(smart_unicode(value['_id']))
            else:
                key_list.append(smart_unicode(value))
        key = "-".join(key_list)
        if key:
            key = get_md5(key) # 可以避免key太长了
        else: # 如果是empty，每次的get_hash_key都是不一样的，意味着直接调用cache_result的，都会失效
            key = '_'

        # 如不匹配，则进行计算，并存入容器
        if key not in getattr(g, cache_name): # 仅判断key的存在，不做key对应的值是否存在
            result = func(*args, **kwargs)
            getattr(g, cache_name)[key] = result

        return getattr(g, cache_name).get(key) # 返回匹配值

    # 写入原函数的一些属性
    _func.__name__ = func.__name__
    _func.func_name = func.func_name
    _func.original_func = func

    return _func



def cache_result(*args, **kwargs):
    prefix = 'cached_by_func_'

    # @cache_result这样直接用
    if len(args) == 1 and hasattr(args[0], '__call__'):
        func = args[0]
        cache_name = prefix + func.func_name
        return cache_wrapper(func, cache_name)

    # @cache_result('key_value')
    elif len(args) == 1 and isinstance(args[0], string_types):
        cache_name = prefix + args[0]
        return curry(cache_wrapper, cache_name=cache_name)

