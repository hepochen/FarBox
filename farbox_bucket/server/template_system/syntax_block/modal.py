# coding: utf8
from farbox_bucket.utils import get_random_html_dom_id
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.template_system.api_template_render import render_api_template


def modal(trigger='', *args, **kwargs):
    # trigger 如果是对innerHTML的处理，就是一个click_dom_id（selector）， 如果是一个url，则是超级链接的title
    caller = kwargs.pop('caller', None)
    if not caller or not hasattr(caller, '__call__'):
        # 不是作为block模式，而是直接调用，可能是GET方式打开一个URL
        url = kwargs.get('url') or ''
        if not url and args:
            url = args[0]
        title = trigger
        if isinstance(url, (str, unicode)):  # 创建一个GET模式的modal的a元素
            dom_id = kwargs.get('id')
            return render_api_template('api_syntax_modal.jade', ajax=True, return_html=True, url=url, title=title,
                                        dom_id=dom_id, **kwargs)
        return ''
    inner_html = caller()
    dom_id = get_random_html_dom_id()
    if trigger and not trigger.startswith('#') and not trigger.startswith('.'):  # id 类型的补足
        trigger = '#' + trigger
    html = render_api_template('api_syntax_modal.jade', inner_html=inner_html, dom_id=dom_id, selector=trigger,
                                return_html=True, **kwargs)
    return html
