# coding: utf8
import os
from farbox_bucket.utils import get_md5_for_file
from farbox_bucket.utils.path import get_relative_path, get_all_sub_files, is_a_hidden_path
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.clouds.qcloud import upload_file_obj_to_qcloud, has_file_on_qcloud, get_file_meta_on_qcloud




def upload_static_files_to_cdn(static_files_root, cdn_static_prefix, secret_id, secret_key,
                               bucket, region, force_update=False):
    sub_filepaths = get_all_sub_files(static_files_root)
    for filepath in sub_filepaths:
        if is_a_hidden_path(filepath):
            continue
        ext = os.path.splitext(filepath)[-1]
        if ext in [".py", ".pyc", ".pyd"]:
            continue
        #print(filepath)
        relative_path = get_relative_path(filepath, static_files_root)
        cnd_path = "/%s/%s" % (cdn_static_prefix.strip("/"), relative_path.strip("/"))
        if not force_update:
            if has_file_on_qcloud(cnd_path, secret_id=secret_id, secret_key=secret_key, bucket=bucket, region=region):
                qcloud_file_meta = get_file_meta_on_qcloud(cnd_path, secret_id=secret_id, secret_key=secret_key, bucket=bucket, region=region)
                if qcloud_file_meta and isinstance(qcloud_file_meta, dict):
                    q_version  = qcloud_file_meta.get("ETag", "").strip("'").strip('"')
                    if q_version and get_md5_for_file(filepath) == q_version:
                        continue
        with open(filepath, "rb") as f:
            upload_file_obj_to_qcloud(file_obj=f,
                                      url_path = cnd_path,
                                      secret_id = secret_id, secret_key=secret_key,
                                      bucket=bucket, region=region, content_type=guess_type(filepath))
        print(filepath)


