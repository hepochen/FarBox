# coding: utf8
import re
from farbox_bucket.utils import smart_unicode, string_types
from farbox_bucket.utils.url import encode_url_arg
from farbox_bucket.server.utils.response import p_redirect, force_redirect_error_handler_callback
from farbox_bucket.server.web_app import app
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request
from flask import make_response, request
from jinja2.environment import Template, TemplateSyntaxError


def response_with_code(content, code):
    response = make_response(content)
    response.status_code = code
    return response


error_500_template_resource = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en-us">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>HTTP 500</title>
</head>
<body>
    <div id="content">
        <div id="error">
            <h1>
                When render this page, errors happened.
            </h1>
    
            <div class="content">
                {% if error %}
                    {{ error }}
                {% else %}
                <p>
                    It's very likely that you used wrong syntax in your template file.
                    And we use <a href="http://jinja.pocoo.org/docs/">Jinja2</a> as our template system.
                </p>
                {% endif %}
    
            </div>
    
        </div>
    </div>
</body>
</html>
"""


error_syntax_error_template_resource = """<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en-us">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>Template Error</title>
    <link href="/__lib/jquery-linedtextarea.css" type="text/css" rel="stylesheet"/>
    <script src="/__lib/jquery.js"></script>
    <script src="/__lib/jquery-linedtextarea.js"></script>
</head>
<body>
    <p style="color:red"> {{message}} </p>
    <textarea class="lined" style="width:100%;min-height: 500px;">{{source}}</textarea>
    <script>
        $(function() {
                    $(".lined").linedtextarea(
                    {selectedLine: {{lineno}}}
                    );
                });
    </script>
</body>
</html>
"""

error_500_template = Template(error_500_template_resource)
error_syntax_error_template = Template(error_syntax_error_template_resource)

@app.errorhandler(500)
def page_error(error):
    debug = False
    template_kwargs = {}
    info = getattr(error, 'description', None)
    if isinstance(info, TemplateSyntaxError):
        debug = True
        template_kwargs = dict(lineno=info.lineno, source=info.source, message=info.message)
    elif isinstance(info, dict) and info.get('debug'):
        debug = True
        template_kwargs = info
    elif isinstance(info, dict) and info.get('frames'):
        # 主要是在 env 里 get_template 对一些函数的预处理出错了
        template = info.get('template')
        frames = info.get('frames') or []
        last_frame = frames[-1]
        if template and hasattr(template, 'source') and last_frame.get('filename', '').lower().endswith('.jade'):
            debug = True
            lineno = last_frame.get('lineno') or 0,
            template_kwargs = dict(
                lineno = lineno,
                source = template.source,
                message = '%s: %s, nearby line %s (but may be not)' % (info.get('type', ''), info.get('value', ''), lineno)
            )
    if debug:
        # 模板写法错误， 相当于起到了 debug 的作用
        e = info
        response = make_response(error_syntax_error_template.render(**template_kwargs))
        response.status_code = 500
        return response
    elif not isinstance(info, string_types):
        info = getattr(error, 'message', 'a internal template error raised')
    if isinstance(info, Exception): # 一般性的错误
        e = info
        message = smart_unicode(e.message)
        message = re.sub(r"(['\"])l_", '\g<1>', message)
        info = message
    response = make_response(error_500_template.render(error = info.replace('\n', '<br/>')))
    response.status_code = 500
    return response


@app.errorhandler(410)
def force_redirect(error):  # 做跳转使用
    # 410 状态, 永久性不可用
    return force_redirect_error_handler_callback(error)



@app.errorhandler(422)
def replace_response(error):
    # 强制 response 的替换，相当于拦截
    new_response = error.description
    return new_response




@app.errorhandler(401)
def auth_failed(error):
    #info = getattr(error, 'description', '')
    return p_redirect('/login?redirect=%s' % encode_url_arg(request.url) )


@app.errorhandler(404)
def page_not_found(error):
    from farbox_bucket.server.bucket_render.render import render_404_for_farbox_bucket
    can_render_user_404_page = True
    if getattr(request, "is_404", False):
        can_render_user_404_page = False
    request.is_404 = True  # 避免由raise_404产生的404再次被死循环调用
    # 404 页面不缓存
    set_not_cache_current_request()
    error = getattr(error, 'description', '')
    not_found_html_for_bucket = "" # empty first
    if can_render_user_404_page:
        not_found_html_for_bucket = render_404_for_farbox_bucket()
    if not not_found_html_for_bucket:
        not_found_html_for_bucket = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>%s</p>
""" % error
    response = response_with_code(not_found_html_for_bucket, 404)
    return response

