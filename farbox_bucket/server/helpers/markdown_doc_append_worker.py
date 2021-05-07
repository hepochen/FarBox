# coding: utf8
import re
import time
from farbox_bucket.utils import string_types, smart_unicode, is_a_markdown_file, to_int
from farbox_bucket.bucket.utils import has_bucket, get_now_from_bucket
from farbox_bucket.bucket.record.utils import get_type_from_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side


def append_to_markdown_doc_and_sync(bucket, path, content, lines_to_append=1, reverse=False,
                                    do_not_repeat=True, lines_more_diff=None, draft_by_default=False):
    # 默认检测 append 的内容是否重复
    if not bucket or not path or not content:
        return
    if not isinstance(bucket, string_types) or not isinstance(path, string_types) or not isinstance(content, string_types):
        return
    if not has_bucket(bucket):
        return
    if not is_a_markdown_file(path):
        return

    content = smart_unicode(content)

    old_doc = get_record_by_path(bucket, path=path) or {}
    if not isinstance(old_doc, dict):
        old_doc = {}

    if lines_more_diff: # 多长时间hi后，自动多一空行
        if old_doc and old_doc.get('timestamp'):
            try:
                diff = time.time() - old_doc.get('timestamp')
                if diff > lines_more_diff:
                    lines_to_append += 1
            except:
                pass

    interval =  '\r\n' * abs(to_int(lines_to_append, max_value=10)) # 间隔换行

    if old_doc:
        if get_type_from_record(old_doc) == 'post': # 目前仅支持日志类型文件的append
            old_content = old_doc.get('raw_content')
            if old_content == " ":
                old_content = ""
            if do_not_repeat:
                if reverse:
                    if old_content.strip().startswith(content.strip()):
                        return ""
                else:
                    old_content_s = old_content.strip()
                    appended_content_s = content.strip()
                    if old_content_s.endswith('\n'+appended_content_s) or old_content_s==appended_content_s:
                        return '' # ignore, 重复的内容不处理
            if reverse: # 插入头部位置
                new_content = '%s%s' % (content, interval)
                content = '%s%s' % (new_content, old_content)
            else:
                new_content = '%s%s' % (interval, content)
                content = '%s%s' % (old_content, new_content)
        else:
            return
    else: # new doc
        content = content.strip()
        if draft_by_default:
            # 新建文档默认是 draft 的状态
            if re.match(u"\w+[:\uff1a]", content): # 可能用户自己声明了 metadata
                content = "status: draft\n%s" % content
            else:
                now = get_now_from_bucket(bucket)
                content = "date: %s\nstatus: draft\n\n%s" % (now, content)

    sync_file_by_server_side(bucket=bucket, relative_path=path, content=content)

    return True  # done
