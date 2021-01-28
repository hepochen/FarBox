# coding: utf8
from __future__ import absolute_import
from werkzeug.formparser import MultiPartParser, FileStorage
import re

# python requests 中上传的内容，虽然通过 files: [file] 进行处理
# 但是也可能最终跑到 form 中，这样原始的数据就破坏了，所以进行patch

_begin_form = 'begin_form'
_begin_file = 'begin_file'
_cont = 'cont'
_end = 'end'
def parse_parts(self, file, boundary, content_length):
    """Generate ``('file', (name, val))`` and
    ``('form', (name, val))`` parts.
    """
    in_memory = 0

    for ellt, ell in self.parse_lines(file, boundary, content_length):
        if ellt == _begin_file:
            headers, name, filename = ell
            is_file = True
            guard_memory = False
            filename, container = self.start_file_streaming(
                filename, headers, content_length)
            _write = container.write

        elif ellt == _begin_form:
            headers, name = ell
            is_file = False
            container = []
            _write = container.append
            guard_memory = self.max_form_memory_size is not None

        elif ellt == _cont:
            _write(ell)
            # if we write into memory and there is a memory size limit we
            # count the number of bytes in memory and raise an exception if
            # there is too much data in memory.
            if guard_memory:
                in_memory += len(ell)
                if in_memory > self.max_form_memory_size:
                    self.in_memory_threshold_reached(in_memory)

        elif ellt == _end:
            if is_file:
                container.seek(0)
                yield ('file',
                       (name, FileStorage(container, filename, name,
                                          headers=headers)))
            else:
                part_charset = self.get_part_charset(headers)
                #yield ('form',
                #       (name, b''.join(container).decode(
                #            part_charset, self.errors)))

                # hepo here starts
                raw_content = b''.join(container)
                content_disposition = headers.get('Content-Disposition')
                if content_disposition and isinstance(content_disposition, (str, unicode)) and \
                        (name == 'file' or 'filename*=' in content_disposition):
                    # 文件类型，不进行unicode转码
                    content = raw_content
                else:
                    content = raw_content.decode(part_charset, self.errors)
                yield ('form', (name, content))
                # hepo here ends

# patch it!!!!!
def patch_werkzeug():
    MultiPartParser.parse_parts = parse_parts




