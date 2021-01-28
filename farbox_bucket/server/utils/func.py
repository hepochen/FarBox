# coding: utf8
from __future__ import absolute_import
import inspect
from farbox_bucket.utils import smart_str, smart_unicode
from farbox_bucket.utils.functional import cached_property


def get_functions_in_a_file_obj(obj):
    obj_filepath = inspect.getmodule(obj).__file__
    functions = []
    sub_functions = inspect.getmembers(obj, inspect.isfunction)
    for sub_function_name, sub_function in sub_functions:
        if sub_function_name.startswith('_') and not sub_function_name.startswith('__') and not sub_function_name=='_': # 以_开头的函数名，不做处理
            # __开头的比较特殊，为了跟系统内置的名称区分开来，比如__int，可能就是一个 int 的调用
            continue
        _real_function = getattr(sub_function, 'original_func', None)  # 可能是被 wrapper 的函数
        real_function = _real_function or sub_function
        if inspect.getmodule(real_function).__file__==obj_filepath:
            functions.append((sub_function_name, sub_function))

            sub_function.arg_spec = inspect.getargspec(real_function)
            sub_function.doc = (inspect.getdoc(real_function) or '').strip()

            if sub_function_name.startswith('__'):
                func_name = sub_function_name
                if func_name != '_':
                    func_name = sub_function_name.lstrip('_')
                functions.append((func_name, sub_function))
    return dict(functions)




class AttrFunc(object):
    # value.int -> to_int(value)
    # value.int(9) -> to_int(value, 9)
    # value.int() -> to_int(value)
    def __init__(self, func):
        self.func = func
        self.is_attr_func = True

    @cached_property
    def default_value(self):
        try:
            return self.func()
        except:
            return smart_unicode(self.func)


    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return smart_unicode(self.default_value)

    def __unicode__(self):
        return smart_unicode(self.default_value)

    def __str__(self):
        return smart_str(self.default_value)

    def __nonzero__(self):
        return bool(self.func)


    def __add__(self, other):
        # 对相加的特殊处理
        if other is None:
            other = ''
        if isinstance(other, (str, unicode)):
            return '%s%s' % (self.default_value, other)
        else:
            return self.default_value + other

    def __mul__(self, other):
        if other is None:
            return ''
        else:
            return self.default_value * other

