# coding: utf8
from farbox_bucket.utils import string_types
from farbox_bucket.utils.functional import curry
from farbox_bucket.server.utils.func import get_functions_in_a_file_obj, AttrFunc


import all as _all_functions
import array as _array_functions
import dictionary as _dict_functions
import strings as _str_functions




all_functions = get_functions_in_a_file_obj(_all_functions)
array_functions = get_functions_in_a_file_obj(_array_functions)
dict_functions = get_functions_in_a_file_obj(_dict_functions)
str_functions = get_functions_in_a_file_obj(_str_functions)

# 特定类型的数据，如果请求其 attr，可以找到对应的functions 进行处理
# 用isinstance(obj, (1,2) or 1) 来判断的，所以是以下的 match table 格式
func_match_rules = [
    [(list, tuple), array_functions],
    [dict, dict_functions],
    (string_types, str_functions),
]


def render_attr_func_without_call(func): # h.xxx 这样的函数可以直接当做属性处理
    if not hasattr(func, '__call__') or not func:
        return func
    if getattr(func, 'is_attr_func', False):
        return func
    new_func = AttrFunc(func)
    return new_func



def get_attr_func(obj, attr, functions):
    # 在一个指定的functions 的 dict 中，试图取得obj.attr 时，返回对应的 function（如果有的话）
    first_arg = None # 被调用的时候隐含的参数，比如posts.sort_by_date, 其中实际调用的是posts.sort 这个属性
    original_func = None
    if attr in functions:
        original_func = functions[attr]
    elif '_by_' in attr: # posts.sort_by_date('-')
        name, first_arg = attr.split('_by_', 1)
        if name in functions:
            original_func = functions[name]
    if original_func:
        wrapped_func = curry(original_func, obj)
        # 不能被 wrap 的函数
        if hasattr(original_func, 'arg_spec'):
            # 比如返回一个 dict(如 humech)，就不能是一个 function 了，或者指定了就是一个属性
            args_length = len(original_func.arg_spec.args)
            if args_length == 1 and not original_func.arg_spec.varargs and not original_func.arg_spec.keywords:
                # 原函数仅仅接收一个参数
                return wrapped_func()
            elif not args_length:
                # 不接受任何参数的， curry 都是不行的, 其实就是相当于一个属性（的函数运行）
                return original_func()
        return wrapped_func


def patch_attr_func_for_obj(obj, attr):
    all_matched_func = get_attr_func(obj, attr, all_functions)
    if all_matched_func:
        return all_matched_func
    for func_types, functions in func_match_rules:
        if isinstance(obj, func_types):
            matched_func = get_attr_func(obj, attr, functions)
            if matched_func is not None:
                return matched_func