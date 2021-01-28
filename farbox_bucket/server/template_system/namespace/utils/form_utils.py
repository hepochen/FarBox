# coding: utf8
from __future__ import absolute_import
import re
import ujson as json
from flask import request
from farbox_bucket.utils import smart_unicode, get_value_from_data, string_to_list, auto_type, to_float, string_types
from farbox_bucket.settings import BASIC_FORM_FORMATS as basic_form_formats
from farbox_bucket.server.utils.response import force_response
from farbox_bucket.server.template_system.api_template_render import render_api_template


TIMEZONES = (
    (-12, 'GMT -12:00'),
    (-11, 'GMT -11:00'),
    (-10, 'GMT -10:00'),
    (-9, 'GMT -09:00'),
    (-8, 'GMT -08:00'),
    (-7, 'GMT -07:00'),
    (-6, 'GMT -06:00'),
    (-5, 'GMT -05:00'),
    (-4, 'GMT -04:00'),
    (-3, 'GMT -03:00'),
    (-2, 'GMT -02:00'),
    (-1, 'GMT -01:00'),
    (0, 'GMT'),
    (1, 'GMT +01:00'),
    (2, 'GMT +02:00'),
    (3, 'GMT +03:00'),
    (3.5, 'GMT +03:30'),
    (4, 'GMT +04:00'),
    (5, 'GMT +05:00'),
    (5.5, 'GMT +05:30'),
    (6, 'GMT +06:00'),
    (6.5, 'GMT +06:30'),
    (7, 'GMT +07:00'),
    (8, 'GMT +08:00'),
    (9, 'GMT +09:00'),
    (9.5, 'GMT +09:30'),
    (10, 'GMT +10:00'),
    (11, 'GMT +11:00'),
    (12, 'GMT +12:00'),
    (13, 'GMT +13:00'),
)



DEFAULT_OPTIONS = {
    'timezone': TIMEZONES,
}



# 提取附属星系， 比如 hello (x=y, k=v) 其中括号内的内容会形成 kv 结构的字典, 仅限单行
def extract_extra_info(line):
    line = line.replace('&quot;', '"').replace('&apos;', "'")
    line = line.replace('<em>', '_').replace('</em>', '_') # 跟Markdown解析后的HTML混淆了，转义回来
    extra_info ={}
    if isinstance(line, string_types) and '\n' not in line and '{' in line and line.endswith('}'): # 对 {}的兼容
        # 因为要提取的内部，是不能包含 () 的， 所以用 {} 进行替换； 但前提是 尾部由 } 结尾，以免造成不必要的处理
        line = line.replace('{', '(').replace('}', ')')
    if isinstance(line, string_types) and '\n' not in line and '(' in line and line.endswith(')'):
        if ',' not in line and '&' in line:
            line = line.replace('&', ',')

        c = re.search(r'(.*?)\((.*?)\)$', line)
        if c:
            new_line, extra_info_s = c.groups()
            line = new_line.strip()
            # lazy_list(type=dom_list, form_keys=[key, value], title='Content')  -> 这个分割比较困难
            if ', ' in extra_info_s: # 为了允许 , 也能用，就要确保field之间的声明用 “, ”，确保后续的空格
                parts = extra_info_s.split(', ')
            else:
                parts = extra_info_s.split(',')
            for extra_info_part in parts:
                if '=' not in extra_info_part:
                    continue
                k, v = extra_info_part.split('=', 1)
                k = k.strip()
                v = v.strip('\'"').strip()
                if re.match('\d+$', v):
                    v = int(v)
                elif re.match(r'\d+\.\d+$', v):
                    v = float(v)
                elif (v.startswith('[') and v.endswith(']')) or (v.startswith('(') and v.endswith(')')): # list
                    v = v[1:-1]
                    v = string_to_list(v)
                elif v.lower() in ['true', 'yes']:
                    v = True
                elif v.lower() in ['false', 'no']:
                    v = False
                extra_info[k] = v
    return line, extra_info



def to_form_fields_obj(data_obj, keys, formats=None, extra_handler_func=None):
    # 将一个 dict, 预处理为可HTML 格式进行编辑的数据，一般是处理 json 的可编辑性
    field_objs_list = []
    formats = formats or {}
    if not isinstance(formats, dict): # 必须是dict类型
        formats = {}

    if basic_form_formats:
        new_formats = basic_form_formats.copy()
        new_formats.update(formats)
        formats = new_formats

    if not isinstance(keys, (tuple, list)):
        return field_objs_list

    for key in keys:
        # 先提取 placeholder, 反引号的方式（头尾边界比较容易判断）
        # placeholder也可能用作他用，比如select的options

        if isinstance(key, dict): # 直接传入的是 dict 类型,不需要特别处理, 但是比较少见
            field_objs_list.append(key)
            continue

        key = smart_unicode(key) # 必须是 unicode
        placeholder = ''
        p_c = re.search('`(.*?)`', key)
        if p_c and 'form_keys=' not in key:
            # form_keys= 不处理 ```, 因为其子元素需要这些信息
            placeholder = p_c.group(1)
            key = re.sub(r'`.*?`', '', key)

        key, extra_info = extract_extra_info(key) # extra_info 是从单个key的括号内提取的内容

        if 'placeholder' in extra_info:
            placeholder = extra_info['placeholder']

        field_type = extra_info.get('type') or '' # 默认, 可能没有提取信息来（单行的话）
        if '@' in key: #  使用@方式，优先级更高
            key, field_type = key.rsplit('@', 1)

        if not field_type and 'password' in key:
            field_type = 'password'

        # key_matched_data 实际上就是formats
        key_matched_data = formats.get(key) or {} # 先处理 format
        if not isinstance(key_matched_data, dict):
            key_matched_data = {}
        key_matched_data = key_matched_data.copy() # copy 避免产生不必要的混乱
        key_matched_data['key'] = key
        field_type = field_type or key_matched_data.get('type') # 原先没有定义 field_type, 从 formats中获得
        if placeholder:
            key_matched_data['placeholder'] = placeholder

        if '.' in key:
            key_title = key.split('.')[-1].replace('_', ' ').title()
        else:
            key_title = key.replace('_', ' ').title()
        if 'Id' in key_title:
            key_title = re.sub(r'( |^)(Id)( |$)', '\g<1>ID\g<3>', key_title)

        key_matched_data['title'] = key_matched_data.get('title') or key_title
        # set value
        default_value = extra_info.get("default") # 默认值
        if default_value is None:
            default_value = key_matched_data.get('default', '')
        if default_value is None: default_value = ''
        value = get_value_from_data(data_obj, key, default=default_value)

        if default_value and isinstance(default_value, string_types) and value=='':
            # 有值，但是空字符串的时候，使用 default_value 来处理
            value = default_value

        if value is None:
            value = ''

        key_matched_data['value'] = value

        if field_type == 'timezone':
            field_type = 'select'

        key_without_dot = key.split('.')[-1]

        if field_type == 'select' and key_without_dot in DEFAULT_OPTIONS:
            key_matched_data['options'] = DEFAULT_OPTIONS[key_without_dot]

        # 类型转换
        if field_type == 'bool': # bool 转为 select 类型
            field_type = 'select'
            key_matched_data['options'] = [('yes', 'Yes'),('no', 'No')]
            key_matched_data['value'] = 'yes' if key_matched_data.get('value') else 'no'
        elif field_type == 'select':
            if placeholder and not key_matched_data.get('options'):
                # 通过placeholder 计算 options
                option_values = [value.strip() for value in placeholder.split(',') if value.strip()]
                if not extra_info.get('index_value', True): # value不为索引
                    key_matched_data['options'] = [(v, v.replace('_', " ")) for v in option_values]
                else: # value为索引值
                    # display_text@key
                    options = []
                    for i, v in enumerate(option_values):
                        if isinstance(v, (str,unicode)):
                            v = v.strip()
                        option = (i+1, v)
                        if v.endswith('@'): # 相当于 显示的内容，即 value本身
                            v = v[:-1] # remove @
                            if isinstance(v, string_types) and len(v)<100 and re.match(r'[.a-z0-9+_-]+$',v, flags=re.I):
                                option = (v, v)
                        if isinstance(v, string_types) and '@' in v:
                            display_text, k = v.split('@', 1)
                            option = (k.strip(), display_text.strip())
                        options.append(option)
                    key_matched_data['options'] = options
            elif not key_matched_data.get('options') and isinstance(value, (list, tuple)):
                # 直接从 list 类型 的 value 中提取
                options = []
                for row in value:
                    if isinstance(row, string_types):
                        options.append([row, row])
                key_matched_data['options'] = options


            # value 可能是整数，就先转为 int、 float 的类型
            if isinstance(value, string_types):
                if re.match(r'\d+$', value):
                    value = int(value)
                    key_matched_data['value'] = value
                elif re.match(r'\d+\.\d+$', value):
                    value = to_float(value)
                    key_matched_data['value'] = value

        elif field_type == 'list': # list 的转为 text，可以用 textarea 来渲染
            key_matched_data['key'] = key+'@list' # 这样 backend 在重新处置这个字段的时候，会转为 list 的类型
            field_type = 'text' # text == textarea
            old_value = key_matched_data.get('value')
            if isinstance(old_value, (list, tuple)):
                value = '\n'.join(old_value)
                key_matched_data['value'] = value

        elif field_type == 'file':
            # 将 placeholder 的内容取出来作为 filepath
            key_matched_data['placeholder'] = 'drag file here to upload/replace'


        # 额外的扩充， 由程序的逻辑控制
        if extra_handler_func and hasattr(extra_handler_func, '__call__'):
            field_type, key_matched_data = extra_handler_func(field_type, key_matched_data)

        if extra_info:
            key_matched_data.update(extra_info)

        # 设定了dom的固定宽度、高度
        for w_h_field in ['height', 'width']:
            w_h_value = key_matched_data.get(w_h_field)
            if w_h_value:
                w_h_value = smart_unicode(w_h_value)[:30].strip()
                if re.match('[\d.]+$', w_h_value):
                    w_h_value += 'px'
                key_matched_data[w_h_field] = w_h_value


        # 某些file_type 比如 category / list 最后都转为HTML类型的field_type
        if field_type:
            key_matched_data['type'] = field_type
        else:
            key_matched_data['type'] = 'default'


        if key_matched_data.get('type') == 'list': # list 类型的value的处理
            if isinstance(key_matched_data.get('value', None), (list, tuple)):
                key_matched_data['value'] = '\n'.join(key_matched_data['value'])

        field_objs_list.append(key_matched_data)
    return field_objs_list



############## for POST starts ##########
def get_pure_form_keys(keys):
    # ‘dd@bool’类型的转为`dd` .etc
    keys = keys or []
    pure_keys = []
    for key in keys:
        if not isinstance(key, string_types):
            continue
        if key in ['_', '-']:
            continue
        key = re.sub(r'`.*?`', '', key)
        key = re.sub(r'\(.*?\)', '', key) # 去除括号内的属性赋值
        key = key.split('@')[0]
        key = key.split(',')[0]
        key = key.split('"')[0].split("'")[0]
        key = key.strip().strip('[]()').strip()
        if key:
            pure_keys.append(key)
    return pure_keys


def get_data_obj_from_POST(keys=None):
    # 从 request.POST 中获得一个dict类型的数据对象
    pure_keys = get_pure_form_keys(keys)
    data_obj = {}
    _data = request.form.to_dict()
    for k, v in _data.items():
        if k.endswith('@list'):
            k = k[:-5]
            v = [row.strip() for row in v.split('\n') if row.strip()]
        elif k.endswith('@json'):
            k = k[:-5]
            try:
                v = json.loads(v)
            except:
                pass
        elif v in['yes', 'no', 'true', 'false']: # bool 性质的
            if v in ['yes', 'true']:
                v = True
            else:
                v = False
        else:
            v = auto_type(v)
            if 'title' in k: # 有 title 关键字的 key, 必须处理为字符串的形式
                v = smart_unicode(v)
            if isinstance(v, int) and v >= 1024000:
                v = smart_unicode(v)
        if k not in pure_keys:
            # 防止多余的参数进来，特别如果是callback_func 直接是一个 db_doc 的 update 函数，会有漏洞
            continue
        else:
            data_obj[k] = v
    return data_obj


############## for POST ends ##########




############## for HTML  starts ##########
def create_form_dom_by_field(field, field_container_class='', **kwargs):
    # field 是一个 to_form_fields_obj 中的一个 数据元素
    html_content = render_api_template('form_dom.jade', field=field, field_container_class=field_container_class,
                                        return_html=True, **kwargs)
    return html_content


def create_form_dom(data_obj, form_keys=None, formats=None, form_key=None):
    if form_key and not form_keys: #  form_key 作为一个backup性质参数使用
        form_keys = form_key
    if isinstance(form_keys, string_types): # 传入的仅仅是一个form_key
        form_keys = [form_keys.strip()]
    if not isinstance(form_keys, (list, tuple)):
        return ''
    if not isinstance(data_obj, dict):
        return ''
    form_keys = [k for k in form_keys if isinstance(k, string_types)]
    fields = to_form_fields_obj(data_obj, keys=form_keys, formats=formats)
    html_content = ''
    for field_obj in fields:
        html_content += create_form_dom_by_field(field_obj)
    return html_content



def create_simple_form(title='', keys=(), data_obj=None, formats=None, info=None, submit_text=None, **kwargs):
    # 自动生成一个 form，但没有自动处理 POST 的能力
    # 变量预处理 starts
    title = title or ''
    if not isinstance(title, string_types) or not isinstance(keys, (list, tuple, dict, str, unicode)):
        return 'parameters error for simple form'

    formats = formats or {}

    if isinstance(keys, string_types):
        # 单 key
        keys = [keys]

    # 默认需要 focus 的元素
    focus_dom_name = kwargs.pop('focus', None)
    if focus_dom_name:
        focus_dom_name = smart_unicode(focus_dom_name)
        focus_dom_name = focus_dom_name.split('#')[0]

    form_fields = to_form_fields_obj(data_obj, keys, formats)

    html_content = render_api_template('form_simple_form.jade', title=title,
                                fields=form_fields, info=info, submit_text=submit_text, focus=focus_dom_name,
                                formats=formats, return_html=True, **kwargs)
    return html_content



def create_grid_form(data_obj=None, keys=None, formats=None, callback_func=None, form_id=None, **kwargs):
    # 主要是会用 pure 进行排版的生成
    if not keys:
        return ''
    do_post = False
    if request.method == 'POST': # 构建 data_obj
        do_post = True
        if form_id and request.args.get('form_id')!=form_id:
            # 可能多个 form 混合，避免 POST 次序混了，确认form_id
            do_post = False

    if do_post:
        data_obj = get_data_obj_from_POST(keys)

        if callback_func: # POST 后的回调函数
            callback_info = callback_func(data_obj)
            if isinstance(callback_info, string_types):
                callback_info = callback_info.strip()
            if callback_info and isinstance(callback_info, string_types):
                kwargs['info'] = callback_info # 这个info会作为grid_form构建html时候的info变量

            if request.values.get('ajax') == 'true': # AJAX 产生的提交, 直接返回请求的结果
                info = callback_info or ''
                return force_response(info, 'text/plain')


    form_fields = to_form_fields_obj(data_obj, keys, formats)

    html_content = render_api_template('form_grid_form.jade', fields=form_fields, form_id=form_id, return_html=True, **kwargs)
    return html_content

############## for HTML  ends ##########

