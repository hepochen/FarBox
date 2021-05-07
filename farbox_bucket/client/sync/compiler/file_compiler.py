#coding: utf8
import time, os
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.settings import MAX_RECORD_SIZE
from farbox_bucket.client.sync.compiler.utils import get_file_timestamp
from farbox_bucket.client.sync.compiler.basic_compiler import BasicSyncCompiler
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.convert.utils import compile_frontend_resource

FRONTEND_EXTS = ['js', 'coffee', 'jade', 'html', 'htm', 'css', 'less', 'scss', 'sass', 'xml', 'json', 'csv']

class FileSyncCompiler(BasicSyncCompiler):
    def __init__(self, *args, **kwargs):
        kwargs['doc_type'] = kwargs.get('doc_type') or 'file'
        BasicSyncCompiler.__init__(self, *args, **kwargs)

    @cached_property
    def file_order_value(self):
        if self.position:
            return self.position * 1000
        else:
            if not self.abs_filepath:
                timestamp = time.time()
            else:
                timestamp = get_file_timestamp(relative_path=self.relative_path, abs_filepath=self.abs_filepath, utc_offset=self.utc_offset)
            return timestamp


    def get_compiled_data(self):
        mime_type = guess_type(self.path)
        if mime_type and mime_type.startswith('image/'):
            file_type = 'image'
        else:
            file_type = 'file'
        data = dict(
            _type = file_type,
            type = file_type,
            _order = self.file_order_value,
        )
        if file_type == 'file':
            # 如果纯粹是 file 类型，且大小在容许的范围内，才尝试将原始内容直接放到 record 内
            ext = os.path.splitext(self.path)[-1].lower().strip('.')
            if ext in FRONTEND_EXTS and len(self.raw_content)<MAX_RECORD_SIZE:
                data.update(dict(
                    raw_content=self.raw_content,
                    raw_content_size=len(self.raw_content),
                    _zipped=False,
                ))
                compiled_type, compiled_content = compile_frontend_resource(ext, raw_content=self.raw_content)
                if compiled_content and compiled_type:
                    data['compiled_type'] = compiled_type
                    data['compiled_content'] = compiled_content
            else:
                raw_content = self.gb64_raw_content
                if len(raw_content) < MAX_RECORD_SIZE:
                    data.update(dict(
                        raw_content=self.gb64_raw_content,
                        raw_content_size=len(self.gb64_raw_content),
                        _zipped=True,
                    ))
        # 而比如 图片，不论大小，全部直传
        return data