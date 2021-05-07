#coding: utf8
import re
import os
import urllib
import time

from farbox_markdown.compile_md import compile_markdown
from farbox_bucket.utils import smart_unicode, smart_str, to_float, count_words, to_int
from farbox_bucket.utils.date import get_local_utc_offset
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.path import get_just_name
from farbox_bucket.utils.date import timestamp_to_date, date_to_timestamp
from farbox_bucket.client.sync.compiler.basic_compiler import BasicSyncCompiler
from farbox_bucket.client.sync.compiler.utils import slugify, get_file_timestamp, string_to_list, get_images_from_html
from farbox_bucket.utils.md_related.markdown_doc_links import get_linked_docs_from_markdown_content


PAGES_TXT_NAMES = ['about', 'links', 'link']

SYSTEM_TEXT_NAMES = ['nav', 'footer', 'comment_js', 'comments_js', 'site']



class PostSyncCompiler(BasicSyncCompiler):
    def __init__(self, *args, **kwargs):
        kwargs['doc_type'] = kwargs.get('doc_type') or 'post'
        BasicSyncCompiler.__init__(self, *args, **kwargs)

    @cached_property
    def just_name(self):
        if self.abs_filepath:
            return get_just_name(self.abs_filepath)
        else:
            return get_just_name(self.relative_path)

    @cached_property
    def compiled_content(self):
        # 编译为 markdown 的内容
        raw_content = self.raw_content
        raw_content = smart_unicode(raw_content[:500000])  # 最多不超过50w字节, 约500k
        raw_content = raw_content.strip().replace(u'\ufeff', '').replace("\r\n", "\n")  # 去除头尾
        post_path = self.path
        if self.real_relative_path:
            post_path = self.real_relative_path
        compiled_content = compile_markdown(raw_content, path=post_path, toc=True)  # markdown编译
        return compiled_content

    @property
    def content(self):
        return self.compiled_content

    @cached_property
    def metadata(self):
        data = getattr(self.compiled_content, 'metadata', {})
        return data



    @cached_property
    def post_status(self):
        # 日志的状态，一般默认为 public
        if not self.slash_number and self.name in PAGES_TXT_NAMES:
            # about / links
            return 'page'
        elif not self.slash_number and self.name in SYSTEM_TEXT_NAMES:
            return 'system'
        elif re.match(r'^_[a-z]{1,20}/', self.path, re.I) and not re.match(r'_posts?/', self.path) \
                and not self.get_meta_value('status'):
            # 位于_xxx 目录下的，默认为status 为 xxx (如果没有声明的话)
            # 但是对_post/_posts下的目录不处理status，兼容Jekyll
            status = self.path.split('/')[0].lower().strip('_')
            return status
        else:
            status = self.get_meta_value(key='status', default='public') or 'public'
            return status.lower()


    @cached_property
    def post_title(self):
        # 获取post的title
        title = self.get_meta_value('title', '')
        # 文中没有声明，看有没有唯一的H1作为title
        if not title and getattr(self.content, 'title', None) and getattr(self.content, 'title_from_post', False):
            title = self.content.title
        if not title:  # 仍然没有title的，就取文件名
            title = self.title  # 保留了大小写
            if guess_type(title):  # 如果是后缀名的，则是把title去掉后缀
                title = os.path.splitext(title)[0]
        return smart_unicode(title.strip())

    @cached_property
    def post_order_value(self):
        # 手工设定的 position， 统一扩大 1000 倍，避免一些浮点数在某些场景下被 int 处理，而颗粒度失真
        order_fields = ['sort', 'order', 'position']
        for field in order_fields:
            order_value = to_float(self.metadata.get(field))
            if order_value is not None:
                # 统一扩大 1000 倍
                return order_value * 1000
        # at last, choose date timestamp as order
        order_value = self.post_timestamp
        return order_value


    @cached_property
    def post_url_path(self):
        url_path = self.get_meta_value('url', '') or self.get_meta_value('url_path', '')
        if url_path and not isinstance(url_path, basestring):
            url_path = smart_unicode(url_path)

        if not url_path:  # 如果是用户自己指定的url，则不管对错，都保存; 反之则是通过relative_path解析一个url
            url_path = self.path.rsplit('.', 1)[0]
            url_path = slugify(url_path, auto=True).lower()  # 不能以slash开头,并且确保小写
        else:  # 用户自己声明的 url，不做大小写处理，保留原始状态
            url_path = slugify(url_path, must_lower=False)  # 替代掉不适合做url的字符

        # url_path是全小写

        if '%' in url_path:
            # 被编码的url，特别是wordpress转过来的
            _url_path = urllib.unquote(smart_str(url_path))
            if url_path != _url_path:
                url_path = smart_unicode(_url_path)

        url_path = url_path.lstrip('/')
        url_path = re.sub(r'/{2,}', '/', url_path)

        url_path = url_path or '--'  # 可能存在空的情况...

        url_path = url_path.strip().lower()

        return url_path


    @cached_property
    def post_timestamp(self):
        if self.abs_filepath:
            timestamp = get_file_timestamp(relative_path=self.relative_path, abs_filepath=self.abs_filepath,
                                           metadata=self.metadata, utc_offset=self.utc_offset)
        elif self.metadata:
            timestamp = get_file_timestamp(relative_path=self.relative_path, abs_filepath=self.abs_filepath,
                                           metadata=self.metadata, utc_offset=self.utc_offset)
        else:
            timestamp = time.time()
        if not timestamp:
            timestamp = time.time()
        return timestamp


    @cached_property
    def post_date(self):
        return timestamp_to_date(self.post_timestamp, is_utc=True)

    @cached_property
    def post_tags(self):
        # every tag is unicode
        tags = self.get_meta_value('tags') or self.get_meta_value('tag')
        tags = string_to_list(tags)
        if not isinstance(tags, (list, tuple)):
            tags = []
        tags = [smart_unicode(tag) for tag in tags] # make sure it's unicode

        # 从 wiki link 语法中提取的 tags
        post_doc_links, wiki_tags = get_linked_docs_from_markdown_content(self.relative_path, self.raw_content)
        for wiki_tag in wiki_tags:
            wiki_tag = smart_unicode(wiki_tag)
            if wiki_tag not in tags:
                tags.append(wiki_tag)

        return tags


    @cached_property
    def post_images(self):
        return get_images_from_html(self.content) or []



    def get_compiled_data(self):
        post_type = 'post'
        if self.just_name in ['index']:
            post_type = 'folder_post'
        data = dict(
            version = self.file_version,
            size = self.file_size,
            title = self.post_title,
            status=self.post_status,
            date=self.post_date,
            raw_content = self.raw_content,
            content = self.compiled_content,
            cover=self.content.cover,
            toc=self.content.toc,

            url_path=self.post_url_path,
            tags = self.post_tags,
            text_length = len(self.raw_content),
            text_words=self.text_words,
            images = self.post_images,
            metadata = self.metadata,

            _type = post_type,
            type = post_type,
            _order=self.post_order_value,
            _utc_offset = get_local_utc_offset(),
        )

        return data


    @cached_property
    def text_words(self):
        return count_words(self.raw_content) or 0



