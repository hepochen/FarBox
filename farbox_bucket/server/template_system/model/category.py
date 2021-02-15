# coding: utf8
import os
from farbox_bucket.utils import smart_unicode, string_types
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.path import get_relative_path, is_sub_path, is_same_path
from farbox_bucket.bucket.utils import get_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.bucket.record.get.folder import get_folder_children_count, get_folder_records
from farbox_bucket.bucket.record.get.tag_related import get_tags_info, get_tags_and_count, get_tags_info_under_path
from farbox_bucket.server.utils.request_path import auto_bucket_url_path
from farbox_bucket.server.template_system.namespace.data import get_data


class Category(object):
    def __init__(self, path_or_record):
        # the record is folder
        self.bucket = get_bucket_in_request_context()
        if isinstance(path_or_record, dict):
            self.raw = path_or_record
            self.path = self.raw.get('path')
        else:
            path = path_or_record
            path = smart_unicode(path).strip()
            self.path = path
            record = get_record_by_path(bucket=self.bucket, path=path) or {}
            self.raw = record
        self.path = self.path.lower()
        if self.raw  and self.raw.get('_type')!='folder':
            # must be folder
            self.raw = {}

    def __nonzero__(self):
        return bool(self.raw)


    def __getattr__(self, item):
        from farbox_bucket.server.template_system.env import SafeUndefined
        if item in self.raw:
            return self.raw.get(item)
        return self.__dict__.get(item, SafeUndefined())


    def __getitem__(self, item):
        return self.__getattr__(item)


    @cached_property
    def tags(self):
        # [(tag, count), (tag, count)]
        tags_info = get_tags_info_under_path(self.bucket, self.path)
        return get_tags_and_count(tags_info)


    @cached_property
    def parents(self):
        return self.parents()

    def get_parents(self, root=None, includes_root=False):
        # 得到所有的上级目录
        ps = []
        if not self.raw:
            return ps
        path_parts = self.path.split('/')[:-1][:50]  # 最多50个层级
        parent_paths = []
        for i in range(len(path_parts)):
            parent_paths.append('/'.join(path_parts[:i + 1]))
        parent_paths.reverse()  # just reverse it for human
        parent_categories = []
        for parent_path in parent_paths:
            if root and not is_sub_path(parent_path, root):
                to_continue = True
                if includes_root and is_same_path(root, parent_path):
                    to_continue = False
                if to_continue:
                    continue
            parent_category = Category(parent_path)
            if parent_category:
                parent_categories.append(parent_category)
        parent_categories.reverse()
        return parent_categories

    @cached_property
    def children(self):
        categories = []
        raw_docs = get_data(path=self.path, type="folder", level=1)
        for raw_doc in raw_docs:
            categories.append(Category(raw_doc))
        return categories

    @cached_property
    def url(self):
        v = u'/category/%s' % self.path
        return auto_bucket_url_path(v)

    def get_url(self, prefix, root=None):
        prefix = prefix.strip("/")
        if not root or not isinstance(root, string_types):
            return "/%s/%s" % (prefix, self.path)
        else:
            relative_path = get_relative_path(self.path.lower(), root.lower(), return_name_if_fail=False)
            if not relative_path:
                return "/%s/%s" % (prefix, self.path)
            else:
                return "/%s/%s" % (prefix, relative_path)

    @cached_property
    def filename(self):
        # 兼容旧的 bitcron
        return self.path


    @cached_property
    def posts_count(self):
        num = get_folder_children_count(self.bucket, self.path, field='posts')
        return num

    @cached_property
    def images_count(self):
        num = get_folder_children_count(self.bucket, self.path, field='images')
        return num

    @cached_property
    def _posts_count(self):
        num = get_folder_children_count(self.bucket, self.path, field='posts', direct=True)
        return num

    @cached_property
    def _images_count(self):
        num = get_folder_children_count(self.bucket, self.path, field='images', direct=True)
        return num

    @cached_property
    def posts(self):
        # 仅仅当前
        pager_name = '%s_child_posts' % self.path
        return get_data(type='post', path=self.path, pager_name=pager_name, level=1)

    @cached_property
    def images(self):
        # 仅仅当前
        pager_name = '%s_child_images' % self.path
        return get_data(type='image', path=self.path, pager_name=pager_name, level=1)


def get_record_parent_category(record):
    if not isinstance(record, dict):
        return None
    data_type = record.get('_type')
    if data_type in ['folder']:
        return None
    path = record.get('path')
    if not path or not isinstance(path, string_types):
        return None
    path = path.replace('\\', '').strip('/')
    parent_path = os.path.split(path)[0]
    category = Category(parent_path)
    return category

