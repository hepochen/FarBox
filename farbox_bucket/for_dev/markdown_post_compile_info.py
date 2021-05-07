#coding: utf8
import os
from farbox_bucket.settings import MAX_RECORD_SIZE
from farbox_bucket.client.sync.compiler_worker import get_compiler_data_directly
from farbox_bucket.utils.data import json_dumps

def get_markdown_post_compiled_info(md_filepath, content_times = 1):
    with open(md_filepath, "rb") as f:
        raw_content = f.read()
    content = raw_content * content_times
    if len(content) > MAX_RECORD_SIZE:
        print("content size too big")
    filename = os.path.split(md_filepath)[-1]
    compiled_data = get_compiler_data_directly(filename, content=content)
    record_size = len(json_dumps(compiled_data))
    print("file_type: %s, zipped:%s, file_size:%s, record_size:%s" %(compiled_data.get("type"),
                                                       compiled_data.get("_zipped"),
                                                       compiled_data.get("size"),
                                                       record_size))


