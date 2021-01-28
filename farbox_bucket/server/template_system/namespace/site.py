# coding: utf8
from flask import g
from farbox_bucket.utils import smart_unicode, get_value_from_data, to_int
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.bucket.utils import get_bucket_files_info, get_bucket_posts_info, get_bucket_pages_configs, get_bucket_site_configs
from farbox_bucket.bucket.record.get.folder import get_folder_children_count
from farbox_bucket.bucket.record.get.tag_related import get_tags_info
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_json_content_by_path
from .html import html as html_namespace_func
from farbox_bucket.server.template_system.namespace.utils.nav_utils import get_nav_items_from_doc, deal_nav_items, \
    get_auto_nav_items, get_nav_items_from_site_configs
from .html import Html

class Site(dict):
    @cached_property
    def html_namespace(self):
        return html_namespace_func()

    @cached_property
    def bucket(self):
        return getattr(g, 'bucket', '')

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


    @cached_property
    def avatar(self):
        if get_record_by_path(self.bucket, 'avatar.png'):
            return '/avatar.png'
        else:
            image_url = '/fb_static/defaults/site_avatar.png'
            return image_url

    @cached_property
    def site_avatar(self):
        return self.avatar

    @cached_property
    def visitor_avatar(self):
        if get_record_by_path(self.bucket, 'visitor.png'):
            return '/visitor.png'
        else:
            image_url = '/fb_static/defaults/visitor.png'
            return image_url


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
        if getattr(g, 'disable_nav', False):  # 当前页面内禁用了 nav 的调用
            return ''

        if meta_doc is None:
            meta_doc = getattr(g, 'doc', {})
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

@cache_result
def site():
    site_obj = Site()
    site_obj.update_site_obj_first()
    return site_obj