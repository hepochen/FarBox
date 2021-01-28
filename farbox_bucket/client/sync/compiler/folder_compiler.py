#coding: utf8
from farbox_bucket.client.sync.compiler.post_compiler import PostSyncCompiler
import os


# folder 从某种角度来说，只是记录这个数据，而不是更多的关系上的，因为无法从 path 上进行查询匹配
# folder_doc

class FolderSyncCompiler(PostSyncCompiler):
    def __init__(self, *args, **kwargs):
        kwargs['doc_type'] = kwargs.get('doc_type') or 'folder'
        PostSyncCompiler.__init__(self, *args, **kwargs)

    def get_compiled_data(self):
        data = PostSyncCompiler.get_compiled_data(self)
        if self.abs_filepath and os.path.isdir(self.abs_filepath):
            folder_relative_path = self.relative_path
        else:
            folder_relative_path = self.relative_path.strip('/')
        data['path'] = folder_relative_path
        data['relative_path'] = folder_relative_path
        data['is_dir'] = True
        data['slash_number'] = folder_relative_path.count('/')
        data['_type'] = 'folder'
        data['type'] = 'folder'
        return data
