#coding: utf8
from __future__ import absolute_import
import time, hashlib
from collections import OrderedDict


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = None # default，实际上不会有 limited 的效果
        fields = ['size_limit', 'limit', 'size', 'max', 'max_size']
        for field in fields:
            field_value = kwds.pop(field, None) # 避免这些字段成为字段的初始对象
            if field_value:
                self.size_limit = field_value
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value, *args, **kwargs):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=True)


def get_md5(content, block_size=0): # 1024*1024 2**20, block_size=1Mb
    if isinstance(content, unicode):
        content = content.encode('utf8')
    if not block_size:
        return hashlib.md5(content).hexdigest()
    else:
        md5_obj = hashlib.md5()
        n = len(content)
        for i in range(0, n, block_size):
            md5_obj.update(content[i:i+block_size])
        return md5_obj.hexdigest()


class cached(object):
    """
    @cached
    def xxxx():
        xxxx

    @cached(60, cache_key=None or other...)
    def xxx():
        xxxxxxx
    """
    def __init__(self, first_arg=None, cache_key=None):
        self.cached_function_responses = {}
        self.direct_func = None
        self.default_cache_key = cache_key

        if hasattr(first_arg, '__call__'):
            # 直接调用了这是
            # @cached
            # def xxxx(): .....
            self.max_age = 0
            self.direct_func = first_arg
        else:
            # 指定了缓存的时间
            # @cached(60)
            # def xxxx(): .......
            if not isinstance(first_arg, int):
                self.max_age = 0
            else:
                self.max_age = first_arg or 0

    def __call__(self, *args, **kwargs):
        def _func(*func_args, **func_kwargs):
            now = time.time()

            if self.direct_func:
                func = self.direct_func
            else:
                func = args[0]

            # 计算缓存的key值，根据传入的函数参数不同可以推断，如果没有函数传入，则相当于func本身的id（整数）
            # func_id 是作为cache_key的base
            if self.default_cache_key:
                base_cache_key = self.default_cache_key
            else:
                base_cache_key = id(func)
            if func_args or func_kwargs:
                # 可能第一个变量传入的是 self 这种实例对象
                func_args_s_list = [] # 形成缓存key用的一个list
                for func_arg in func_args:
                    if not isinstance(func_arg, (str, unicode, dict, tuple, list, bool, int, float)):
                        func_args_s_list.append(str(id(func_arg)))
                    else:
                        func_args_s_list.append(func_arg)
                var_key = '-'.join(func_args_s_list) + str(func_kwargs)
                var_md5 = get_md5(var_key)
                cache_key = '%s-%s' % (base_cache_key, var_md5)
            else:
                cache_key = base_cache_key

            if cache_key in self.cached_function_responses:
                cached_obj = self.cached_function_responses[cache_key]
                cached_data = cached_obj['data']
                cached_time = cached_obj['cache_time']
                if not self.max_age: # 相当于直接缓存，没有过期时间
                    return cached_data
                else: # 查看是否过期
                    if now - cached_time < self.max_age:
                        return cached_data
            result = func(*func_args, **func_kwargs)
            self.cached_function_responses[cache_key] = dict(data=result, cache_time=now)
            return result

        if self.direct_func:
            return _func(*args, **kwargs)
        else:
            return _func