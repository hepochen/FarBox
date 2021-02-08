# coding: utf8
import re
import uuid
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.utils import get_random_html_dom_id



def tab(keys, active=1, **kwargs):
    # +tab(keys=[a, b, c], active=1)
    #   #tab
    #   #tab
    #   #tab.etc

    caller = kwargs.pop('caller', None)
    if not caller or not hasattr(caller, '__call__'):
        return ''
    if not isinstance(keys, (list, tuple)) or not keys:
        return ''
    dom_id = get_random_html_dom_id()
    inner_html = caller()
    real_tabs_count = inner_html.count('<div id="tab">')
    keys = keys[:real_tabs_count]
    if len(keys) <=1: # 只有一个，没有处理为tab的需要
        return inner_html
    for i in range(len(keys)):
        tab_dom_id = '%s-%s' % (dom_id, i)
         # 替换模板默认的tab id
        inner_html = re.sub(r'(<div )([^<>]*?id=[\'"])(tab\d*)([\'"])', '\g<1> class=tab_item \g<2>%s\g<4>'%tab_dom_id, inner_html, count=1)
    html = render_api_template('api_tab.jade',
                                keys=keys, dom_id=dom_id, active=active, inner_html=inner_html,
                                return_html=True, **kwargs)

    return html





