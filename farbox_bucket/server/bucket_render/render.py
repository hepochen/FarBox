# coding: utf8
import re
from flask import abort, Response
from flask.globals import _request_ctx_stack
from jinja2.exceptions import TemplateNotFound
from farbox_bucket.settings import STATIC_FILE_VERSION, DEBUG

from farbox_bucket.utils import get_md5
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils.cache import LimitedSizeDict
from farbox_bucket.utils.convert.jade2jinja import jade_to_template
from farbox_bucket.utils.gevent_utils import get_result_by_gevent_with_timeout_block

from farbox_bucket.bucket.utils import get_admin_bucket, set_bucket_in_request_context, get_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_record_by_url

from farbox_bucket.server.utils.request_path import get_request_path
from farbox_bucket.server.utils.site_resource import get_site_config, get_site_configs, has_template_by_name
from farbox_bucket.server.utils.response_html import insert_into_footer, insert_into_header

from farbox_bucket.server.template_system.env import farbox_bucket_env
from farbox_bucket.server.template_system.app_functions.after_request.cache_page import get_response_from_memcache
from farbox_bucket.server.template_system.api_template_render import render_api_template_as_response

from farbox_bucket.server.static.static_render import send_static_frontend_resource

from farbox_bucket.server.bucket_render.builtin_theme._render import show_builtin_theme_as_sub_site
from farbox_bucket.server.utils.request_context_vars import reset_loads_in_page_in_request, set_not_cache_current_request
from farbox_bucket.server.template_system.namespace.html import Html

from .static_file import render_as_static_resource_in_pages_for_farbox_bucket, render_as_static_file_for_farbox_bucket


html_content_for_timeout_page = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n<title>408 Request Timeout</title>\n<h1>Request Timeout</h1>\n<p>Sorry! The run time of this page is too long, maybe there were some errors in your template</p>\n'

def render_html_content_for_timeout_page(reqctx):
    with reqctx:
        set_not_cache_current_request()
        return Response(html_content_for_timeout_page)

def render_template_for_farbox_bucket_with_context(reqctx, **kwargs):
    #appctx = _app_ctx_stack.top
    #with appctx:
    with reqctx:
        return render_template_for_farbox_bucket(**kwargs)


def render_template_for_farbox_bucket_by_gevent(**kwargs):
    #appctx = _app_ctx_stack.top
    reqctx = _request_ctx_stack.top
    result_html = get_result_by_gevent_with_timeout_block(
        curry(render_template_for_farbox_bucket_with_context, reqctx=reqctx, **kwargs),
        timeout = 3,
        fallback_function = curry(render_html_content_for_timeout_page, reqctx=reqctx),
        auto_kill = True,
        raise_error = True,
    )
    return result_html



def after_render_template_for_farbox_bucket(html):
    html = re.sub(r'([ \t]*\n){10,}', '\n', html)  # 去除多余的空行, 模板引擎造成的
    html = after_render_html(html)
    return html


def render_template_for_farbox_bucket(**kwargs):
    #import time; time.sleep(5) # test timeout
    request_path = get_request_path()
    template_name = request_path.strip('/')
    if not template_name:
        template_name = 'index'
    try:
        template = farbox_bucket_env.get_template(template_name)
        html = template.render(**kwargs)
        return after_render_template_for_farbox_bucket(html)
    except TemplateNotFound as e:
        # 尝试走一些 builtin themes
        sub_site_html = show_builtin_theme_as_sub_site()
        if sub_site_html:
            return after_render_template_for_farbox_bucket(sub_site_html)
        bucket = get_bucket_in_request_context()
        hide_post_prefix = get_site_config('hide_post_prefix', default_value=False)
        if bucket and hide_post_prefix: # 不带 /post 前缀的
            post_doc = get_record_by_url(bucket, template_name)
            if post_doc:
                try: post_template = farbox_bucket_env.get_template("post")
                except: post_template = None
                if post_template:
                    html = post_template.render(**kwargs)
                    return after_render_template_for_farbox_bucket(html)
        if e.name == "index":
            abort(404, Html.i18n("please custom your template or choose a theme for site first, no homepage found."))
        else:
            if request_path.strip("/") == "feed" and not has_template_by_name("feed"):
                # 如果没有自定义 feed 页面，系统默认配置的
                return render_api_template_as_response("feed.jade")
            else:
                abort(404, 'not found for %s' % e.name)
    except Exception as e:
        raise e


def render_404_for_farbox_bucket():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return
    try:
        reset_loads_in_page_in_request()
        template = farbox_bucket_env.get_template("404")
        html = template.render()
        return html
    except:
        return





def render_bucket(bucket, web_path=""):
    set_bucket_in_request_context(bucket)
    try: # memcache 的获取，也可能会出错, 概率很低
        cached_response = get_response_from_memcache()
        if cached_response:
            return cached_response
    except:
        pass
    if not web_path:
        web_path = get_request_path()

    # admin bucket 的默认主页对应
    if not web_path or web_path == "/":
        if bucket == get_admin_bucket() and not has_template_by_name("index"):
            return render_api_template_as_response("page_admin_default_homepage.jade")

    static_file_response = render_as_static_resource_in_pages_for_farbox_bucket(web_path)
    if not static_file_response and web_path.lstrip('/').startswith('template/'):
        # 对一些 template 目录下的兼容
        web_path_without_prefix = web_path.lstrip('/').replace('template/', '', 1)
        static_file_response = render_as_static_resource_in_pages_for_farbox_bucket(web_path_without_prefix)
    if static_file_response:
        return static_file_response
    else:
        file_response = render_as_static_file_for_farbox_bucket(web_path)
        if file_response:
            return file_response
        if web_path and '.' in web_path:
            static_response_from_system = send_static_frontend_resource(try_direct_path=True)
            if static_response_from_system:
                return static_response_from_system

        #if DEBUG: return render_template_for_farbox_bucket()

        return render_template_for_farbox_bucket_by_gevent()
        #return render_template_for_farbox_bucket()



STATIC_FILE_VERSION_GET_VAR = '?version=%s' % STATIC_FILE_VERSION

############ for markdown scripts starts ############


mathjax_script = """
<script type= "text/javascript">
    window.MathJax = {
      tex: {
        inlineMath: [ ['$','$']],
        displayMath: [ ['$$','$$'] ]
      },
      svg: {fontCache: 'global'},
      startup: {
            ready: () => {
              MathJax.startup.defaultReady();
              MathJax.startup.promise.then(() => {
                if (typeof(send_to_app_client)!='undefined'){send_to_app_client({'action': 'start_to_export_pdf'})}
              });
            }
          },
      options: {
        renderActions: {
          addMenu: [0]
        }
      }
    };
</script>
<script type="text/javascript" src="/__lib/markdown_js/mathjax/tex-svg.js%s"></script>

""" % STATIC_FILE_VERSION_GET_VAR

echarts_script = '<script type="text/javascript" src="/__lib/markdown_js/echarts.min.js%s"></script>' % STATIC_FILE_VERSION_GET_VAR

mermaid_script = """'<script type="text/javascript" src="/__lib/markdown_js/mermaid/mermaid.min.js%s"></script>
<link rel="stylesheet" href="/__lib/markdown_js/mermaid/mermaid.css%s">
<script>mermaid.initialize({startOnLoad:true});</script>""" % (STATIC_FILE_VERSION_GET_VAR, STATIC_FILE_VERSION_GET_VAR)

def after_render_html(html):
    if '</body>' not in html:
        return html
    html = render_code_blocks_inside(html) # ```code jade_template```
    site_configs = get_site_configs()
    echarts = site_configs.get('echarts')
    mathjax = site_configs.get('mathjax')
    mermaid = site_configs.get('mermaid')
    if echarts:
        html = insert_into_header(echarts_script, html)
    if mathjax:
        html = insert_into_footer(mathjax_script, html)
    if mermaid:
        html = insert_into_footer(mermaid_script, html)
    inject_template = site_configs.get("inject_template") or ""
    inject_template = inject_template.strip()
    if inject_template:
        html = html.replace('</body>', '\n%s\n</body>'%inject_template, 1)
    return html


############ for markdown scripts ends ############




############# embed_in jade template for markdown doc starts ########
env_templates_cache = LimitedSizeDict(size_limit=10000)
def get_template_by_env(source, try_jade=True):
    # 由某个指定的 env，解析 template, 并处理 cache
    template_key = get_md5(source)
    if template_key in env_templates_cache:
        return env_templates_cache[template_key]
    if try_jade:
        try:
            template = jade_to_template(source, env=farbox_bucket_env)
        except:
            template = farbox_bucket_env.from_string('<b style="color:red">`code` block means template source code,'
                                       ' error format will break current page!!</b>')
    else:
        template = farbox_bucket_env.from_string(source)
    env_templates_cache[template_key] = template
    return template

def _render_template_in_html_func(match_obj):
    #raw = match_obj.group()
    template_source = match_obj.groups()[1].strip()
    template_source = template_source.replace('&lt;', '<').replace("&gt;", '>')
    template = get_template_by_env(template_source, try_jade=True)
    return template.render()
    #return '`code` block means template source code, error format will break current page!!'
    #try:
    #    return template.render()
    #except:
    #    return raw


def render_code_blocks_inside(html):
    new_html = re.sub(r'(<pre class="lang_code"><code>)(.*?)(</code></pre>)',
                  _render_template_in_html_func, html, flags=re.M|re.S)
    return new_html

############# embed_in jade template for markdown doc ends ########