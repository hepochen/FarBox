# coding: utf8
import json, re
from flask import request
from farbox_bucket.utils import get_value_from_data, to_int, string_types
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.bucket.private_configs import update_bucket_private_configs, get_bucket_private_configs_by_keys
from farbox_bucket.bucket.utils import get_bucket_files_info, get_bucket_posts_info, get_bucket_pages_configs, \
    get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.record.get.folder import get_folder_children_count
from farbox_bucket.bucket.record.get.tag_related import get_tags_info
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_json_content_by_path, has_record_by_path
from farbox_bucket.server.utils.request import need_login
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side
from farbox_bucket.server.template_system.namespace.utils.nav_utils import get_nav_items_from_doc, deal_nav_items, \
    get_auto_nav_items, get_nav_items_from_site_configs
from farbox_bucket.server.bucket_render._keys_config_info import builtin_site_settings_keys_config_info
from farbox_bucket.server.utils.request_context_vars import get_doc_in_request
from .html import Html
from .html import html as html_namespace_func
from .data import data as data_namespace_func

class Site(dict):
    @cached_property
    def html_namespace(self):
        return html_namespace_func()

    @cached_property
    def data_namespace(self):
        return data_namespace_func()

    @cached_property
    def bucket(self):
        return get_bucket_in_request_context()

    @cached_property
    def _files_info(self):
        return get_bucket_files_info(self.bucket) or {}

    @cached_property
    def _tags_info(self):
        # k:v --> tag: [path1, path2]
        return get_tags_info(self.bucket)

    @cached_property
    def _posts_info(self):
        return get_bucket_posts_info(self.bucket)


    @cached_property
    def files(self):
        return self._files_info


    @cached_property
    def tags(self):
        # [(tag, count), (tag, count)]
        result = []
        for tag, tag_paths in self._tags_info.items():
            if not tag_paths:
                continue
            if not isinstance(tag_paths, (list, tuple)):
                continue
            result.append([tag, len(tag_paths)])
        return result

    @cached_property
    def text_words(self):
        text_words = to_int(self._posts_info.get('text_words'), default_if_fail=0)
        return  text_words

    def update_site_obj_first(self):
        site_obj = get_bucket_site_configs(self.bucket)
        if isinstance(site_obj, dict):
            self.update(site_obj)

    def count_folder(self, folder_path, field='posts'):
        return get_folder_children_count(self.bucket, folder_path, field=field)


    def get_image_url(self, filename, default_value=None):
        if has_record_by_path(self.bucket, filename):
            return '/%s' % filename
        elif has_record_by_path(self.bucket, '_direct/%s'%filename):
            return '/_direct/%s' % filename
        else:
            if default_value:
                return default_value
            else:
                image_url = '/fb_static/defaults/%s' % filename
                return image_url

    @cached_property
    def avatar(self):
        return self.get_image_url("avatar.png")


    @cached_property
    def background_image(self):
        return self.get_image_url("bg.jpg")


    @cached_property
    def site_avatar(self):
        return self.get_image_url("site_avatar.png")

    @cached_property
    def visitor_avatar(self):
        return self.get_image_url("visitor.png")

    @cached_property
    def admin_avatar(self):
        return self.get_image_url("admin.png")

    @cached_property
    def favicon(self):
        return self.get_image_url("favicon.icon")


    @cached_property
    def title(self):
        return self.get('title') or 'Site Title'


    @cached_property
    def pages_configs(self):
        configs = get_bucket_pages_configs(self.bucket) or {}
        return configs


    ############# 导航相关 starts ##########
    @cached_property
    def nav_configs(self):
        nav_config = get_json_content_by_path(self.bucket, 'nav.json') or {}
        nav_configs = nav_config.get('nav_configs') or []
        return nav_configs

    @cached_property
    def nav_disabled(self):
        nav_config = get_json_content_by_path(self.bucket, 'nav.json') or {}
        return nav_config.get('user_nav_disabled', False)

    @cached_property
    def nav(self):
        return self.get_nav(toggle_menu=True)

    @cached_property
    def just_nav(self):
        return self.get_nav(load_front_sources=False)

    def get_nav(self, meta_doc=None, items=None, as_items=False, load_front_sources=True, toggle_menu=False,  **scss_vars):
        #if getattr(g, 'disable_nav', False):  # 当前页面内禁用了 nav 的调用
        #    return ''

        if meta_doc is None:
            meta_doc =  get_doc_in_request()
        if meta_doc and get_value_from_data(meta_doc, 'metadata.disable_nav'):
            # 有上下文doc，并且禁用了导航
            return ''

        nav_items = get_nav_items_from_site_configs(self.bucket)  # 用户自己设定的

        nav_items_in_doc = get_nav_items_from_doc(meta_doc)
        if nav_items_in_doc:  # 当前文档定义的导航，优先级高
            nav_items = nav_items_in_doc

        if not nav_items:
            # items这边变量一般是设计师传入了，相当于默认的导航；如果没有，则是自动生成的导航
            nav_items = deal_nav_items(items) or get_auto_nav_items(self.bucket)

        if as_items:
            # 直接返回原始的 list，以供模板进一步定义
            return nav_items
        else:  # 渲染为 HTML 的结果返回
            return Html.get_nav(nav_items, load_front_sources=load_front_sources, toggle_menu=toggle_menu, **scss_vars)

    ############# 导航相关 ends ##########

    def get_settings_from_json(self, config_path):
        if not isinstance(config_path, string_types):
            return {}
        if not re.match("__\w+\.json", config_path):
            return {}
        if not self.bucket:
            return {}
        settings_from_json = get_json_content_by_path(self.bucket, config_path)
        if not isinstance(settings_from_json, dict):
            settings_from_json = {}
        return settings_from_json


    def get_settings_keys_config(self, keys_config_path):
        if not isinstance(keys_config_path, string_types):
            return {}
        keys_config = get_json_content_by_path(self.bucket, keys_config_path) or builtin_site_settings_keys_config_info.get(keys_config_path)
        if not isinstance(keys_config, dict):
            keys_config = {}
        return keys_config


    def settings_json_editor(self, keys_config_path, private_config_keys=None, formats=None, **kwargs):
        # 对站点的 config 文件的编辑
        # 如果指定了 private_config_keys， 则只是更新到非公开的 update_bucket_private_configs
        if not self.bucket:
            return ""
        logined = need_login(bucket=self.bucket)
        if not logined:
            return ""
        if private_config_keys and not isinstance(private_config_keys, (list, tuple)):
            private_config_keys = None
        keys_config = self.get_settings_keys_config(keys_config_path)
        if keys_config_path in builtin_site_settings_keys_config_info:
            private_config_keys_for_builtin = keys_config.get("private_keys")
            if private_config_keys_for_builtin:
                private_config_keys = private_config_keys_for_builtin

        hide_submit_button = False
        config_store_path = None
        config_keys = None
        if keys_config and isinstance(keys_config, dict):
            config_store_path = keys_config.get("path")
            config_keys = keys_config.get("keys")
            hide_submit_button = keys_config.get("hide_submit_button", False)

        if not private_config_keys:
            if not isinstance(config_store_path, string_types) or not isinstance(config_keys, (list, tuple)):
                return "config_keys format error, not allowed"
            if not config_store_path or not config_keys:
                return "config_store_path is invalid or config_keys is invalid, not allowed"
            if not re.match("__\w+\.json", config_store_path):
                return "path should be __xxxx.json, not allowed"

        def settings_json_editor_callback(new_data_obj):
            for key, value in new_data_obj.items():
                if value and isinstance(value, (str, unicode)) and len(value) > 20000:
                    return 'error: the length of value is too long'
            if private_config_keys:
                private_configs_to_update = {key: new_data_obj.get(key) for key in private_config_keys}
                update_bucket_private_configs(self.bucket, **private_configs_to_update)
            else:
                content = json.dumps(new_data_obj, indent=4)
                sync_file_by_server_side(bucket=self.bucket, relative_path=config_store_path, content=content)


        if request.method != "POST":
            # 处理 data
            if private_config_keys:
                data_obj = get_bucket_private_configs_by_keys(self.bucket, private_config_keys)
            else:
                data_obj = get_json_content_by_path(self.bucket, config_store_path) or {}
            if not isinstance(data_obj, dict): # 必须是 dict 类型，否则数据会被重置
                data_obj = {}
        else:
            data_obj = None # will get from request.form automatic

        formats = formats or {}

        return Html.grid_form(data_obj, config_keys, formats=formats,
                              callback_func=settings_json_editor_callback,
                              hide_submit_button=hide_submit_button, **kwargs)



@cache_result
def site():
    site_obj = Site()
    site_obj.update_site_obj_first()
    return site_obj