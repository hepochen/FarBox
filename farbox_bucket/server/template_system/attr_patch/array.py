#coding: utf8
from __future__ import absolute_import
import operator
from farbox_bucket.utils import get_value_from_data, split_list, to_int, smart_str, smart_unicode, string_types


def all_has(objects, key, check_value=None, opt=None):
    """objects是一个list，内个element都是dict，并且都有指定key对应的值"""
    if not objects:
        return False
    for obj in objects[:200]: # 最多200个元素
        if not isinstance(obj, dict):
            return False
        if check_value is None and obj.get(key) is None: # 没有设定check_value，则值为None，则匹配失败
            return False
        elif check_value is not None:
            value_got = obj.get(key)
            if isinstance(value_got, (tuple,list)): # 如果得到的结果是列表，则比对的是其元素长度，因为列表本身没有比较的意义
                value_got = len(value_got)
            if (opt is None or opt=='==') and value_got!=check_value: # 没有设定opt，则只要不等于则匹配失败
                return  False
            elif opt=='>=' and value_got<check_value: # 期望是value_got >= check_value, 结果value_got < check_value，匹配失败
                return False
            elif opt=='<=' and value_got>check_value:
                return False
            elif opt=='>' and value_got<=check_value:
                return False
            elif opt=='<' and value_got>=check_value:
                return False
    return True




##### sort_by

def sort(objects, attr='position', ordered_attr=None, ordered_keys=None, match=False):
    # todo 现在没有 position 这个字段了
    if attr.startswith('-'):
        reverse = True
        attr = attr.lstrip('-')
    else:
        reverse = False
    if reverse == '-':
        reverse = True
    if attr:
        new_objects = sorted(objects, key=lambda o: get_value_from_data(o, attr))
    else:
        new_objects = objects # 原始的就可以了。
    if reverse:
        new_objects.reverse()

    if ordered_attr and ordered_keys and isinstance(ordered_attr, string_types) and isinstance(ordered_keys, (list, tuple)):
        # objects 中每个 object 中如果有 ordered_attr 这个属性，并且对应的 value 在 ordered_keys 中进行排序
        ordered_keys = [k for k in ordered_keys if isinstance(k, string_types)]
        objects_map = {get_value_from_data(obj, ordered_attr):obj for obj in new_objects}
        head_objects = []
        for key in ordered_keys:
            key_matched_obj = objects_map.get(key)
            if key_matched_obj is not None:
                head_objects.append(key_matched_obj)
                try: new_objects.remove(key_matched_obj)
                except: pass
        if match: # 仅仅处理 ordered_keys 的逻辑
            return head_objects
        return head_objects + new_objects

    return new_objects




##### group
def _get_sort_key(value, per=10):
    # 将一个value转为可排序的key 值
    # value通常是一个list, per作为阶乘积， 比如[5,2] -> 5*10+2*1= 52
    # 比如年、月、日
    # 主要在group函数中，处理attr:sub1+sub2的这种方式，比如date:year+month
    if type(value) in [tuple, list]:
        is_number = True
        ls = value
        for row in ls:
            if type(row) not in [float, int]:
                is_number = False
                break
        if is_number:
            total = 0
            pos = len(ls)
            for i in ls:
                total += i * per**(pos-1)
                pos -= 1
            return total
        else:
            return ','.join([str(row) for row in ls])
    else:
        return value


def group(objects, attr, *args, **kwargs):
    """
    list
    """
    if attr.startswith('-'):
        reverse = True
        attr = attr.lstrip('-')
    else:
        reverse = kwargs.pop('reverse', False)

    group_sorts = kwargs.pop('group_sorts', None) or []

    key = smart_str(attr)
    parts = key.split(':', 1)
    attr = parts[0]
    sub_attrs = [row.strip() for row in parts[1].split('+')] if len(parts) == 2 else [] # : 表示有子属性，由+进行分割多个字段

    # 使用相同的key值，grouped存objects, grouped_sort存排序的key
    grouped = {}
    grouped_sort = {}

    def add_source(group_name): # 添加源到一个 group 上
        grouped.setdefault(group_name,[]).append(obj)  # 组别, 然后添加到这个 group 中
        if group_name not in grouped_sort:  # 组别的排序, sort_key 是一个可排序的，一般会处理为整数
            grouped_sort[group_name] = sort_key

    for obj in objects:
        if not sub_attrs:  # 没有子属性复合的，直接属性, 比如 group(posts, 'date')， 或者 group(posts, 'date.year')
            sort_key = sort_value = get_value_from_data(obj, attr)  # 不一定是basestring类型的
            if type(sort_value) in [list, tuple]:  # 目前是tags的处理
                # 如果sort_key是一个list，则里面每一个都会分组
                for group_name in sort_value:
                    add_source(group_name)
            else:
                add_source(group_name=sort_value)
        else: # 很可能是复合属性
            parent = get_value_from_data(obj, attr)
            sort_values = []
            for sub_attr in sub_attrs:
                sort_values.append(get_value_from_data(parent, sub_attr))
            sort_values = tuple([value for value in sort_values if value])
            if len(sort_values) == 1:
                sort_values = sort_values[0]
            elif not sort_values:
                sort_values = ''  # 避免返回()这样的值

            sort_key = _get_sort_key(sort_values, per=100)

            add_source(group_name=sort_values) # 以values作为group_name

    # 得到根据sort_key排序了的group_names相关的二元数组
    grouped_sort = sorted(grouped_sort.iteritems(), key=operator.itemgetter(1), reverse=reverse)
    # 获得已经排序成功的group_names
    sorted_group_names = [group_name for group_name, sort_key in grouped_sort]
    # 返回最终结果

    to_return = []
    sorted_groups = []
    unsorted_groups = []
    for group_name in sorted_group_names:
        one_group = [group_name, grouped.get(group_name)]
        to_return.append(one_group)
        if group_sorts:
            if group_name in group_sorts:
                sorted_groups.append(one_group)
            else:
                unsorted_groups.append(one_group)

    if group_sorts:
        sorted_groups.sort(lambda x,y: group_sorts.index(x[0])-group_sorts.index(y[0]))
        to_return = sorted_groups + unsorted_groups

    return to_return






def insert(objects, to_insert, position=-1): # 默认插入最后
    #if isinstance(to_insert, (list, tuple)):
        #return ''
    if isinstance(to_insert, dict) and to_insert.get('_id'):
        to_insert_id = to_insert.get('_id')
        for obj in objects:
            if isinstance(obj, dict) and obj.get('_id') == to_insert_id:
                objects.remove(obj)
                break
    if to_insert:
        try:
            objects.insert(position, to_insert)
        except:
            objects.append(to_insert)
    return '' # 对objects的id没有操作，返回空值



#### filter
def __filter(objects, attr=None, attr_value=None, opt=None, return_one=False, **kwargs):
    # posts.filter_by_date('2013-12-14'.date, '>=')
    # posts.filter_by_tag('test', 'in')
    if not attr and not attr_value and kwargs:
        attr = kwargs.keys()[0]
        attr_value = kwargs.values()[0]
    if attr is None:
        return objects
    if len(objects) > 2000: # 最大尺寸限制
        objects = objects[:2000]
    if isinstance(attr_value, (list, tuple)): # in for list
        result = filter(lambda obj: get_value_from_data(obj, attr) in attr_value, objects)
    elif attr and isinstance(attr, (str, unicode)):
        filtered_objects = []
        for row in objects:
            value_got = get_value_from_data(row, attr)
            if opt == 'in' and isinstance(attr_value, (str, unicode, int, float)):
                if isinstance(value_got, (list, tuple)) and attr_value in value_got:
                    filtered_objects.append(row)
            elif opt in ['>=', '=>'] and value_got>=attr_value:
                filtered_objects.append(row)
            elif opt in ['<=', '=<'] and value_got<=attr_value:
                filtered_objects.append(row)
            elif not opt:
                if isinstance(value_got, (list, tuple)) and not isinstance(attr_value, (list, tuple)):
                    # like filter(posts, 'tag', 'test')
                    if attr_value in value_got:
                        filtered_objects.append(row)
                else:
                    if type(attr_value) == bool: # boolean 类型的特殊处理
                        if attr_value == bool(value_got):
                            filtered_objects.append(row)
                    elif attr_value == value_got:
                        filtered_objects.append(row)
        result = filtered_objects
    else:
        result = []
    if return_one:
        if result:
            return result[0]
        else:
            return  None
    else:
        return result


def join(objects, link_str=' '):
    link_str = smart_unicode(link_str)
    if all([isinstance(obj, (str, unicode, int, float)) for obj in objects]):
        # 内部元素，必须都是字符串类型的
        objects = [smart_unicode(obj) for obj in objects]
        return link_str.join(objects)
    else:
        return objects


def length(objects):
    return len(objects)



def split(objects, per=3):
    per = to_int(per, min_value=1) or 3
    return split_list(objects, per)


for func in [length]:
    func.is_just_property = True