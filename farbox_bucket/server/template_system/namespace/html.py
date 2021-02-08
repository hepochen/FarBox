# coding: utf8
from __future__ import absolute_import
import os
import uuid
import re
from flask import request
from farbox_bucket.bucket.utils import get_bucket_in_request_context
from farbox_bucket.i18n import default_i18n_data
from farbox_bucket.settings import STATIC_FILE_VERSION

from farbox_bucket.utils import smart_unicode, get_md5, is_str, to_int, get_value_from_data, string_types
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.url import join_url
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.html import html_escape, linebreaks as _linebreaks
from farbox_bucket.utils.path import get_relative_path
from farbox_bucket.utils.env import get_env
from farbox_bucket.clouds.qcloud import sign_qcloud_url

from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.record_and_paginator.paginator import get_paginator
from farbox_bucket.server.utils.request import get_language
from farbox_bucket.server.utils.site_resource import get_pages_configs, get_site_configs
from farbox_bucket.server.utils.request_context_vars import is_resource_in_loads_in_page_already,\
    get_i18n_data_from_request, set_i18n_data_to_request
from farbox_bucket.server.utils.request_path import auto_bucket_url_path, get_request_path_for_bucket

from farbox_bucket.server.static.static_render import web_static_resources_map, static_folder_path
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.server.template_system.namespace.utils.form_utils import create_simple_form, create_grid_form, \
    create_form_dom_by_field as _create_form_dom_by_field, create_form_dom as _create_form_dom, \
    get_data_obj_from_POST as form_get_data_obj_from_POST

from farbox_bucket.server.template_system.namespace.utils.nav_utils import pre_nav_data
from farbox_bucket.server.helpers.smart_scss import get_smart_scss_url

from farbox_bucket.server.realtime.utils import get_bucket_ws_url


static_files_url = (get_env("static_files_url") or "").strip().strip("/")
qcloud_cdn_token = (get_env("qcloud_cdn_token") or "").strip()



def get_a_random_dom_id():
    dom_id = 'd%s' % uuid.uuid1().hex
    return dom_id


lazy_load_map = {
    'font': '/fb_static/lib/fontawesome/css/font-awesome.min.css',
    'jquery': '/fb_static/lib/jquery.js',
    'pure': ['/fb_static/lib/pure.css', '/fb_static/lib/pure_patch.css'],
    'form': '/fb_static/lib/wtf-forms.css',
    'markdown': '/fb_static/lib/markdown/markdown.css',
    'essage': ['/fb_static/lib/essage/essage.css', '/fb_static/lib/essage/essage.js'],
    'opensans': '/fb_static/lib/fonts/open_sans.css',
    'open_sans': '/fb_static/lib/fonts/open_sans.css',
    'merriweather': '/fb_static/lib/fonts/merriweather.css',
    'animate': '/fb_static/lib/animate.3.5.2.min.css',
    'animation': '/fb_static/lib/animate.3.5.2.min.css',
    'donghua': '/fb_static/lib/animate.3.5.2.min.css',
    "post_preview": "/fb_static/basic/post_preview.css",

}


def str_has(obj, to_check, just_in=False):
    if isinstance(to_check, (tuple, list)): # 给的是一个list，只要其中一个元素满足就可以了
        for sub_to_check in to_check[:100]: # 最多检测100项
            if isinstance(sub_to_check, (unicode, str)) and str_has(obj, sub_to_check, just_in=just_in):
                return True

    if not isinstance(obj, (unicode, str)):
        return False
    if not isinstance(to_check, (unicode, str)):
        return False
    to_check = to_check.strip().lower()
    obj = obj.strip().lower()
    to_check_start = to_check.strip()+' '
    to_check_end = ' ' + to_check.strip()
    if just_in:
        return to_check in obj
    elif is_str(to_check):
        if obj == to_check or obj.startswith(to_check_start) or obj.endswith(to_check_end):
            return True
        else:
            return False
    else: # 中文的，没有空格
        return to_check in obj


class Html(object):

    def url(self, url_path):
        return auto_bucket_url_path(url_path)

    @classmethod
    def load(cls, *resource, **kwargs):
        if getattr(request, 'disable_load_func', False): # load函数被禁用了
            return ''

        force_load = kwargs.pop('force', False)

        if not resource:
            return ''

        if len(resource) == 1:
            resource = resource[0]
            if resource in lazy_load_map:  # 快捷方式
                resource = lazy_load_map[resource]
            if ' ' in resource: # load('a b c')的处理
                resource = resource.split(' ')

        # resource 可以是一个 list，也可以是字符串
        # 预先进行类型判断
        if isinstance(resource, (list, tuple)):
            result = ''
            for child_resource in resource:
                if isinstance(child_resource, string_types):
                    result += cls.load(child_resource)
            return result
        elif not isinstance(resource, string_types):
            return ''

        # 确保进入以下流程的都是单个 resource，这样才能达到去重的效果

        # 处理 smart scss 的问题
        if kwargs.pop("scss", False):
            scss_compiled_url = get_smart_scss_url(resource, **kwargs)
            resource = scss_compiled_url

        #相同的 resource，一个页面内，仅允许载入一次
        if is_resource_in_loads_in_page_already(resource) and not force_load:
            # ignore, 页面内已经载入过一次了
            return ""

        if not isinstance(resource, string_types):
            return resource

        # like h.load('jquery')
        if '.' not in resource and resource in web_static_resources_map:
            match_local_filepath = web_static_resources_map[resource]
            #match_filename = os.path.split(match_local_filepath)[-1].lower()
            relative_path = get_relative_path(match_local_filepath, root=static_folder_path)
            resource = '/__%s' % relative_path

        # url 的相对位置关系的调整~
        raw_resource = resource
        resource = auto_bucket_url_path(resource)

        # 增加 ?version 的逻辑
        if '?' not in resource:
            if resource.startswith('/__'):
                resource = '%s?version=%s' % (resource, STATIC_FILE_VERSION)
            elif '/fb_static/' in resource:
                resource = '%s?version=%s' % (resource, STATIC_FILE_VERSION)
            elif raw_resource.startswith('/template/'):
                template_pages_configs = get_pages_configs()
                template_version = template_pages_configs.get('mtime')
                if template_version:
                    resource = '%s?version=%s' % (resource, template_version)

        resource_path = resource
        if '?' in resource:
            resource_path = resource.split('?')[0]
        ext = os.path.splitext(resource_path)[1].lower()
        if not ext:
            ext = '.%s' % (resource.split('?')[0].split('/')[-1]) # 比如http://fonts.useso.com/css?family=Lato:300

        if static_files_url and resource.startswith("/fb_static/"):
            static_relative_path = resource.replace("/fb_static/", "", 1)
            static_url = "%s/%s" % (static_files_url, static_relative_path)
            resource = static_url

        if ext in ['.js', '.coffee'] or ext.startswith('.js?') or resource.split('?')[0].endswith('js'):
            content = '<script type="text/javascript" src="%s"></script>' % resource
        elif ext in ['.css', '.less', '.scss', '.sass'] or ext.startswith('.css?') or ext.endswith('?format=css'):
            content = '<link href="%s" type="text/css" rel="stylesheet"/>' % resource
        else:
            content = ''

        return content



    def linebreaks(self, content):
        content = smart_unicode(content)[:50000]
        return _linebreaks(content)

    @property
    def random_dom_id(self):
        # 返回一个随机的dom_id
        return 'd_%s' % uuid.uuid4().hex


    def get_dom_id(self, v=None):
        # 将一个value转为dom_id的格式
        return 'dd_%s' % get_md5(v)

    @staticmethod
    def join_url(url, *args, **kwargs):
        new_url = join_url(url, **kwargs)
        return new_url



    @staticmethod
    def js_view(title, url=None, group_id=None, view_type='', **kwargs):
        if url is None:
            # 默认值, 这样图片调用的时候, 只要一个传入就可以了
            url = title

        url = smart_unicode(url)
        if isinstance(title, (tuple, list)) and len(title) == 2:
            title, thumbnail = title # 图片类型的
        else:
            title = smart_unicode(title)
            mime_type = guess_type(title) or ''
            if mime_type.startswith('image/'):
                thumbnail = title # title 本身就是一张图片
                title = kwargs.get('alt') or os.path.split(title)[-1] # 文件名作为 title
                title = smart_unicode(title)
            else:
                thumbnail = ''

        if not view_type: # 自动推断
            if thumbnail:
                view_type = 'image'
            elif url.endswith('.mp4'):
                view_type = 'video'
            else:
                link_mime_type = guess_type(url) or ''
                if link_mime_type.startswith('image/'):
                    view_type = 'image'
                else:
                    view_type = 'iframe'

        class_name = kwargs.get('class_name') or ''
        css_class = 'js_view js_view_%s %s' % (view_type, class_name)
        if group_id:
            css_class += ' js_view_group '
        else:
            group_id = ''

        dom_id = get_a_random_dom_id()
        html_content = render_api_template('js_view', view_type=view_type,
                                    title=title, thumbnail=thumbnail, url=url, css_class=css_class, uuid=dom_id, group_id=group_id,
                                    return_html=True, **kwargs)
        return html_content



    @classmethod
    def a(cls, title, url=None, dom_id=None, must_equal=False, **kwargs):
        # 自动生成 a 元素, 主要是能产生是否 select 等属性
        # 如果不是全equal的，则只要这个起头就可以了
        classes = smart_unicode(kwargs.get('class', '') or '') or ''
        more_classes = ' ' + smart_unicode(kwargs.get('class_name', '') or '')
        classes += more_classes
        selected_classes = classes + ' selected active current'
        url = url or kwargs.get('href')
        url = auto_bucket_url_path(url)
        url = smart_unicode(url)
        title = smart_unicode(title)
        if dom_id:
            dom_id = smart_unicode(dom_id)
        if url.startswith('mailto:'):
            a_properties = ''
        elif '://' not in url and not url.startswith('#'):  # 自动补全成一个站点内的url
            url = '/' + url.lstrip('/')
            url = re.sub(r'/+', '/', url)
            a_properties = ''
        elif url.startswith('#'):
            a_properties = ''
        else:
            a_properties = 'target=_blank'
        target = kwargs.get('target')
        if target and 'target' not in a_properties and isinstance(target, string_types) and '"' not in target:
            a_properties += ' target="%s"' % target
        url = smart_unicode(url)
        # 不要设定 title，可能 a 内嵌的是一个 html 片段
        style = kwargs.get('style', '')
        html_for_selected = '<a href="%s" class="%s" %s>%s</a>' % (url, selected_classes, a_properties, title)
        html_for_normal = '<a href="%s" class="%s"  %s>%s</a>' % (url, classes, a_properties, title)
        if style:
            html_for_selected = html_for_selected.replace('>', ' style="%s" >' % style, 1)
            html_for_normal = html_for_normal.replace('>', ' style="%s" >' % style, 1)

        request_url = (request.path + '?' + smart_unicode(request.query_string)) if request.query_string else request.path
        request_url = re.sub(r'/page/\d+/?$', '/', request_url)
        url_to_check = url.split('#')[0]
        if must_equal:
            html_content = html_for_selected if url_to_check == request_url else html_for_normal
        else:
            if get_request_path_for_bucket(url) != '/':
                html_content = html_for_selected if request_url.startswith(url_to_check) else html_for_normal
            else:
                html_content = html_for_selected if request_url == url_to_check else html_for_normal
        if dom_id:
            html_content = '<a id="%s"' % dom_id + html_content[2:]
        return html_content

    @classmethod
    def auto_a(cls, title, href, a_title=None, class_name='', group_id='', target='', dom_id=None, **kwargs):
        # 跟 js_view 关联起来, a_title=alter_title； 如果不是和 js_view 则会使用a这个生成函数
        href_mime_type = guess_type(href)
        use_js_view = False
        view_type = 'iframe'
        group_id = group_id or kwargs.pop('group', '') or ''
        dom_id = dom_id or get_a_random_dom_id()

        # 特殊 URL 的对应，因为某些场景（smartpage）中不方便定义 a_title 这个逻辑
        special_protocols = ['qrcode', 'iframe']
        for special_protocol in special_protocols:
            special_protocol_prefix = '%s://' % special_protocol
            if href.startswith(special_protocol_prefix):
                a_title = special_protocol
                href = href.replace(special_protocol_prefix, '', 1).strip()
                if '://' not in href:  # 本 site 内的url，确保以 / 开头
                    href = '/%s' % href.lstrip('/')

        if not class_name:
            class_name = kwargs.pop('class', '')

        title_mime_type = guess_type(title)
        if title_mime_type and title_mime_type.startswith('image/'):
            # 自动转为图片的 html 片段
            image_as_title = '<img src="%s">' % title
        else:
            image_as_title = title

        if title and href and isinstance(title, string_types) and isinstance(href, string_types):
            if href.endswith('.mp4'):
                # 视频的封面是图片
                return cls.js_view(image_as_title, href, view_type='video', class_name=class_name)
            if href.endswith('.swf') or str_has(href, ['vimeo.com/video', 'youtube.com', 'youku.com', 'tudou.com'],
                                                just_in=True):
                use_js_view = True
            elif href.startswith('.') or href.startswith('#') and len(href.strip()) != 1:
                view_type = 'modal'
                use_js_view = True
            elif a_title == 'iframe' or str_has(href, ['gdgdocs.org', 'jinshuju', 'mikecrm.com'], just_in=True):
                use_js_view = True
            elif a_title in ["qrcode", "erweima"]:
                use_js_view = True
                view_type = 'qrcode'
            elif href_mime_type.startswith('image/'):
                use_js_view = True
                view_type = 'image'
            if use_js_view:
                return cls.js_view(title, href, view_type=view_type, class_name=class_name,
                                   group_id=group_id, target=target, dom_id=dom_id, **kwargs)
            else:
                return cls.a(image_as_title, href, class_name=class_name, target=target, dom_id=dom_id, **kwargs)
        else:
            return ''  # failed


    @staticmethod
    def paginator(paginator=None, style='simple', **kwargs):
        if 'simple' in kwargs and not kwargs.get('simple'):
            # 对旧的兼容，最开始的时候，auto 风格的调用是 simple=False
            style = 'auto'
        # 构建上下页的label，当然本身也是可以传入 HTML 片段的
        if 'pre_label' not in kwargs:
            if style == 'mini':
                pre_label = '<'
            else:
                pre_label = '&laquo; Prev'
            kwargs['pre_label'] = pre_label
        if 'next_label' not in kwargs:
            if style == 'mini':
                next_label = '>'
            else:
                next_label = 'Next &raquo;'
            kwargs['next_label'] = next_label

        paginator = paginator or get_paginator()
        if not paginator:
            return ''  # ignore

        return render_api_template('paginator',
                                   paginator=paginator, paginator_style=style, return_html=True, **kwargs)



    def back_to_top(self, label=u'△'):
        # 页面右下角的返回顶部
        html_content = render_api_template('back_to_top', label=label, return_html=True)
        return html_content


    def auto_toc(self, post=None, **kwargs):
        # for markdown
        post_type = post.get('_type') or post.get('type')
        if not post or not isinstance(post, dict) or post_type not in ['post', 'folder_post', 'folder']:
            return ''
        if not post.get('toc'):
            return ''
        html_content = render_api_template('auto_toc', post=post, **kwargs)
        return html_content


    def nav(self, *nav_data, **kwargs):
        toggle_menu = kwargs.get('toggle_menu', False)
        return self.get_nav(nav_data, load_front_sources=True, toggle_menu=toggle_menu)

    @staticmethod
    def get_nav(nav_data, load_front_sources=True, toggle_menu=False, **scss_vars):
        if not isinstance(nav_data, (list, tuple)):
            return ''
        nav_data = pre_nav_data(nav_data)
        if not nav_data:
            return ''
        first_item = nav_data[0]
        if isinstance(first_item, dict):
            nav_type = 'full'
        else:
            nav_type = 'plain'
        # 跟 site.get_nav 接近的逻辑
        # auto_frontend 表示默认载入前端资源
        # scss_vars 是 menu 的 scss 替换
        html_content = render_api_template('api_namespace_html_nav.jade', nav_data=nav_data, nav_type=nav_type,
                                        load_front_sources=load_front_sources, toggle_menu=toggle_menu, return_html=True,
                                           scss_vars=scss_vars,
                                         )
        return html_content



    def auto_sidebar(self, side='left', sidebar_name='sidebar', width=300, default_status="hide"):
        # for markdown
        if side not in ['left', 'right']:
            side = 'left'
        width = to_int(width, 300)
        html = render_api_template('auto_sidebar', sidebar_name=sidebar_name,
                                    side=side, sidebar_width=width, default_status=default_status, return_html=True)
        return html


    @staticmethod
    def i18n(key, *args):
        key = smart_unicode(key)
        if not args:
            # 获取
            if key.startswith('_'):  # 以_开头的，摘1后，返回原值
                return key[1:]
            lang = get_language()
            key1 = '%s-%s' % (key, lang)
            i18n_data = get_i18n_data_from_request()
            matched_value = i18n_data.get(key1) or i18n_data.get(key)
            if not matched_value:
                matched_lang_data = default_i18n_data.get(lang) or {}
                if matched_lang_data:
                    matched_value = matched_lang_data.get(key)
            return matched_value or key
        elif len(args) <= 2:
            if len(args) == 2:  # 指定了 lang 的
                value, lang = args
                lang = smart_unicode(lang).strip().lower()
                key = '%s-%s' % (key, lang)
            else:  # 没有指定lang，设定默认值
                value = args[0]
            set_i18n_data_to_request(key, value)
            # 设置的
        # at last
        return ''

    @cached_property
    def headers(self):
        return self.mobile_metas + self.seo()

    @cached_property
    def mobile_metas(self):
        return """
           <meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0" name="viewport"/>
           <meta content="yes" name="apple-mobile-web-app-capable"/>
           <meta content="black" name="apple-mobile-web-app-status-bar-style"/>
           <meta content="telephone=no" name="format-detection"/>
           <meta name="renderer" content="webkit">\n"""

    def set_meta(self, key, value):
        # 生成 HTML 的 head_meta
        if not key or not value:
            return ''
        key = smart_unicode(key).replace('"', "'")
        value = html_escape(smart_unicode(value).replace('"', "'"))
        meta_content = '<meta name="%s" content="%s">\n' % (key, value)
        return meta_content

    def set_metas(self, **kwargs):
        html_content = ''
        for k, v in kwargs.items():
            html_content += self.set_meta(k, v)
        return html_content

    def seo(self, keywords=None, description=None):
        if getattr(request, 'seo_header_set_already', False):
            # 在一个页面内，仅仅能运行一次, 会被 h.headers 调用，如果要使用seo，确保 seo 在之前运行
            return ''
        site_configs = get_site_configs()
        keywords = keywords or get_value_from_data(request, 'doc.metadata.keywords')\
                   or get_value_from_data(site_configs, 'keywords')
        if isinstance(keywords, (list, tuple)):  # keywords 是一个list
            keywords = [smart_unicode(k) for k in keywords]
            keywords = ', '.join(keywords)
        description = description or get_value_from_data(request, 'doc.metadata.description') or \
                      get_value_from_data(site_configs,'description')
        html_content = self.set_metas(keywords=keywords, description=description)
        request.seo_header_set_already = True
        return html_content


    def debug(self):
        bucket = get_bucket_in_request_context()
        if not bucket:
            return ''
        js_script_content = self.load('/__realtime.js') + self.load('/__debug_template.js')
        js_script_content += '<script>connect_to_ws_by_listen_files("%s")</script>' % get_bucket_ws_url(bucket)
        return js_script_content

    @staticmethod
    def ajax(dom_id, url, method='get', data='', callback=''):
        # 能够在模板中直接生成 ajax 的代码逻辑
        # 向 url 发送 method 的请求，data 为 data, callback是一个本地的 js 函数名称
        # 即使在一个 list 中，我们也认为 dom_id 是可以界定的，即使最终生成的代码看起来累赘，实际并没有什么性能问题
        url = smart_unicode(url)
        if "'" in url:
            return "' is not allowed be included in a url"

        dom_id = smart_unicode(dom_id)

        method = smart_unicode(method).lower()
        if method not in ['get', 'post', 'delete', 'update']:
            method = 'get'

        if data:
            data = json_dumps(data)
        html_content = render_api_template('ajax.jade', url=url, method=method,
                                            data=data, callback=callback, dom_id=dom_id)
        return html_content





    def show(self, template_path, *args,  **kwargs):
        from farbox_bucket.server.template_system.env import render_by_farbox_bucket_env
        # 显示一个子模板, 作为 html 的部分
        # todo Bitcron 默认提供了  waterfall 的 layout，这部分应该后期是增强 Markdown 扩展的重要入口！！
        template_path = smart_unicode(template_path).lower().strip('/')
        template_path = 'show/' + template_path # show 作为前缀
        html_content = render_by_farbox_bucket_env(template_path, **kwargs)
        if html_content:
            html_content = '<div class="h_show">\n%s\n</div>\n' % html_content
        return html_content



    ########### form starts #########
    def ajax_submit(self, **kwargs):
        return render_api_template('ajax_submit.jade', **kwargs)

    @staticmethod
    def get_form_data(keys):
        if not isinstance(keys, (list, tuple)):
            return {}
        return form_get_data_obj_from_POST(keys)

    @staticmethod
    def simple_form(title='', keys=(), data_obj=None, formats=None, info=None, submit_text=None, **kwargs):
        return create_simple_form(title=title, keys=keys, data_obj=data_obj, formats=formats,
                                  info=info, submit_text=submit_text, **kwargs)

    @staticmethod
    def grid_form(data_obj=None, keys=None, formats=None, callback_func=None, form_id=None, ajax=True, **kwargs):
        kwargs["ajax"] = ajax
        return create_grid_form(data_obj=data_obj, keys=keys, formats=formats, callback_func=callback_func,
                                form_id=form_id, **kwargs)

    @staticmethod
    def create_form_dom_by_field(field, field_container_class='', **kwargs):
        return _create_form_dom_by_field(field=field, field_container_class=field_container_class, **kwargs)

    @staticmethod
    def create_form_dom(data_obj, form_keys=None, formats=None, form_key=None):
        return _create_form_dom(data_obj=data_obj, form_keys=form_keys, formats=formats, form_key=form_key)

    ########### form ends #########




@cache_result
def html():
    return Html()


@cache_result
def h():
    return html()
