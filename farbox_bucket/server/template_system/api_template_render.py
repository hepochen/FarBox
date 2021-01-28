# coding: utf8
from farbox_bucket.settings import DEBUG, sentry_client
from farbox_bucket.utils import smart_unicode, get_md5
from farbox_bucket.utils.cache import LimitedSizeDict
from farbox_bucket.server.template_system.templates.info import api_templates
from werkzeug.exceptions import HTTPException
from flask import Response
from jinja2.sandbox import SandboxedEnvironment

api_template_env = None

def get_api_template_env():
    from farbox_bucket.server.template_system.env import FarboxBucketEnvironment
    global api_template_env
    if not api_template_env:
        api_template_env = FarboxBucketEnvironment() # SandboxedEnvironment
    return api_template_env



template_source_cache = LimitedSizeDict(size=500)

def render_template_source(template_source, *args, **kwargs):
    if not template_source:
        return ''
    try:
        api_template_env = get_api_template_env()
        template_source_md5 = get_md5(template_source)
        template = template_source_cache.get(template_source_md5)
        if not template:
            template = api_template_env.from_string(template_source)
            template_source_cache[template_source_md5] = template
        html_content = template.render(*args, **kwargs)
    except HTTPException as e:  # 410 是内部用来跳转用得
        raise e
    except Exception as e:
        if DEBUG:
            raise e
        if sentry_client:
            sentry_client.captureException()
        html_content = '<div style="color:red">api template error</div>'
    return html_content



def render_api_template(name, *args, **kwargs):
    name = name.replace('.jade', '')
    template_source = api_templates.get(name, '')
    template_source = smart_unicode(template_source)
    return render_template_source(template_source, *args, **kwargs)


def render_api_template_as_response(name, *args, **kwargs):
    html = render_api_template(name, *args, **kwargs)
    return Response(html)
