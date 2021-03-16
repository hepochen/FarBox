# coding: utf8
from farbox_bucket.client.sync.compiler.basic_compiler import BasicSyncCompiler
from farbox_bucket.utils.data import csv_to_list, csv_data_to_objects

# 解析 _data/visits.csv 文件，并转为相应的 data 数据
# server 端对于这个 data，会截取前 1000，作为 visits 的逻辑

class VisitsSyncCompiler(BasicSyncCompiler):
    def __init__(self, *args, **kwargs):
        kwargs['doc_type'] = kwargs.get('doc_type') or 'visits'
        BasicSyncCompiler.__init__(self, *args, **kwargs)

    def get_compiled_data(self):
        data_list = csv_to_list(self.raw_content,
                                                 max_rows=10001,  # 1w条记录最多
                                                 max_columns=50,
                                                 auto_fill=True
                                                 )
        objects = csv_data_to_objects(data_list)
        data = dict(
            objects = objects,
            raw_content = self.raw_content,
            data=data_list,
        )
        return data

