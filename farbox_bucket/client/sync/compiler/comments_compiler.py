# coding: utf8
import time, os
from farbox_bucket.client.sync.compiler.basic_compiler import BasicSyncCompiler
from farbox_bucket.utils.data import csv_to_list, csv_data_to_objects



class CommentsSyncCompiler(BasicSyncCompiler):
    def __init__(self, *args, **kwargs):
        kwargs['doc_type'] = kwargs.get('doc_type') or 'comments'
        BasicSyncCompiler.__init__(self, *args, **kwargs)

    def get_compiled_data(self):
        data_list = csv_to_list(self.raw_content,
                                                 max_rows=1000,  # 1k条记录最多
                                                 max_columns=50,
                                                 auto_fill=True
                                                 )
        objects = csv_data_to_objects(data_list)
        _order_value = time.time()
        if self.abs_filepath and os.path.isfile(self.abs_filepath):
            _order_value = os.path.getmtime(self.abs_filepath)
        data = dict(
            _order = _order_value,
            objects = objects,
            raw_content = self.raw_content,
            data = data_list,
        )
        return data
