# coding: utf8
from flask import request
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.response import force_response
from farbox_bucket.server.template_system.api_template_render import render_api_template




def page(*sub_args, **kwargs):
    caller = kwargs.pop('caller', None)
    if caller and request.args.get('pjax', '').lower() == 'true' and hasattr(caller, '__call__'):
        # pjax 下的时候，仅仅处理 caller 下的内容，这样就不会引入冗余的 html，从而直接 ajax append 即可
        return force_response(caller())
    html = render_api_template('api_syntax_page.jade', caller=caller, return_html=True, **kwargs)
    return html
