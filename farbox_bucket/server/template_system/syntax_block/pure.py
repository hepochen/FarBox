# coding: utf8
import re
from farbox_bucket.utils import smart_unicode, to_int, to_float
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.template_system.namespace.html import Html

special_grid_factors = {
    0.2: '1/5',
    0.4: '2/5',
    0.6: '3/5',
    0.8: '4/5',
}
def get_grid_factor(k, base=24, odd_base=5):
    # 一般有两套，比如 1/5 就对应不到 24 中
    k = special_grid_factors.get(k) or k

    if not k:
        return k, base

    if isinstance(k, (str,unicode)):
        if '-' in k or '/' in k:
            v1, v2 = re.split(r'[-/]', k, maxsplit=1)
            v1 = to_int(v1)
            v2 = to_int(v2)
            if v1 and v2:
                small_one = min(v1, v2)
                big_one = max(v1, v2)
                if big_one == odd_base:
                    base = odd_base
                k = float(small_one)/float(big_one)
        elif '.' in k:
            k = to_float(k)
        else: # 整数
            k = to_int(k) or 1

    if k and isinstance(k, int) and k>1:
        k = float(k)/base

    if isinstance(k, (float, int)) and k<=1:
        # 之前全部处理为分数了, 这样 1 就是全值了
        k *= base

    # 处理最终的 k 值
    k = to_int(round(k)) or base # 四舍五入并 int
    if k > base:
        k = base
    if k < 1:
        k = 1
    return k, base



# jinja2 2.9+ 之后，就不用写成渲染器的模式
def pure(*args, **kwargs): # 对 pure css 的处理
    do_grid = True
    caller = kwargs.pop('caller', None)
    if not caller or not hasattr(caller, '__call__'):
        return ''
    inner_html = caller()

    factors_devices = ['pure-u', # 总是,  # 全填满的时候相当于phone
                       'pure-u-sm', # ≥ 568px  # phone 横
                       'pure-u-md', # ≥ 768px  # ipad
                       'pure-u-lg', # ≥ 1024px # ipad 横 & 普通桌面
                       'pure-u-xl', # ≥ 1280px # 大桌面
                       ]
    html_class = smart_unicode(kwargs.get('class') or '')
    html_class_list = html_class.split('.')
    html_class = ' '.join(html_class_list)
    if len(args):
        for i, raw_factor in enumerate(args):
            grid_factor = get_grid_factor(raw_factor)
            grid_value, grid_base = grid_factor
            try: prefix = factors_devices[i]
            except: break
            grid_class = '%s-%s-%s' % (prefix, grid_value, grid_base)
            html_class += ' %s'%grid_class
        do_grid = False
    if do_grid: # 外部的 grid 包裹
        return '%s\n<div class="pure-g">\n%s\n</div>' % (Html.load('pure'), inner_html)
    else: # 某个具体 grid
        html_class = html_class.replace('"', '') + ' pure_cell'
        return '\n<div class="%s">\n%s\n</div>' % (html_class, inner_html)