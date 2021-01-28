# coding: utf8
from farbox_bucket.utils.convert.coffee2js import compile_coffee
from farbox_bucket.utils.convert.css import compile_css
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html


def compile_frontend_resource(ext, raw_content):
    ext = ext.lower().strip('.')
    if ext in ['less', 'scss', 'sass']:
        func = compile_css
        compiled_type = 'text/css'
    elif ext in ['coffee']:
        func = compile_coffee
        compiled_type = 'text/javascript'
    elif ext in ['jade']:
        func = convert_jade_to_html
        compiled_type = 'text/html'
    else:
        func = ''
        compiled_type = ''
    if func:
        try:
            compiled_content = func(raw_content)
        except:
            compiled_content = ''
    else:
        compiled_content = ''
    return compiled_type, compiled_content