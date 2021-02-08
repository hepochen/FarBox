# coding: utf8
import re
from farbox_bucket.utils.functional import curry
from jinja2.runtime import Undefined
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.template_system.namespace.data import Data
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.utils import get_random_html_dom_id



def slider(folder=None, doc_type='image', **kwargs):
    if doc_type not in ['post', 'image']:
        doc_type = 'image'
    if folder and isinstance(folder, (str, unicode)):
        docs = Data.get_data(path=folder, type=doc_type, level=1, with_page=False, limit=10, sort='position')
    else:
        docs = []

    caller = kwargs.pop('caller', None)
    if not caller or not hasattr(caller, '__call__'):  # 相当于直接的函数调用
        inner_html = ''
    else:
        inner_html = caller() or ''

    elements = []

    # turn docs into elements
    for doc in docs:
        element = render_api_template('api_slider_doc_element.jade', doc=doc, return_html=True, **kwargs)
        element = element.strip()
        if element:
            elements.append(element)

    dom_id = get_random_html_dom_id()

    height = kwargs.get('height') or '500px'
    nav_bottom = kwargs.get('nav_bottom') or '30px'
    block_css_style = "#%s .slider_element, #%s .unslider, #%s .bitcron_slider{height: %s} #%s .unslider-nav{bottom: %s}" % \
                      (dom_id, dom_id, dom_id, height, dom_id, nav_bottom)

    if inner_html:
        # 有 inner_html 的，进行某些标记性质的切割，获得 elements
        raw_elements = inner_html.split('<div class="slider_end"></div>')
        for raw_element in raw_elements:
            element = raw_element.strip()
            if element:
                elements.append(element)

    # slider 的动效等基本设定
    autoplay = kwargs.pop('autoplay', True)
    if isinstance(autoplay, Undefined): autoplay = True
    show_arrows = kwargs.pop('show_arrows', True)
    if isinstance(show_arrows, Undefined): show_arrows = True
    animation = kwargs.pop('animation', '')
    if isinstance(animation, Undefined): animation = ''
    show_image_title = kwargs.pop('show_image_title', False)
    html = render_api_template('api_slider.jade', elements=elements, dom_id=dom_id,
                               block_css_style=block_css_style,
                               autoplay=autoplay, show_arrows=show_arrows, animation=animation,
                               show_image_title=show_image_title,
                               return_html=True, **kwargs)

    return html
