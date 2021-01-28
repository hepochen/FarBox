# coding: utf8
from farbox_bucket.utils.ssdb_utils import hdel, hclear
from farbox_bucket.bucket.utils import remove_bucket_from_buckets, clear_related_buckets
from farbox_bucket.bucket.record.get.helper import loop_records_for_bucket
from farbox_bucket.bucket.storage.default import storage



def delete_bucket(bucket, delete_files=True):
    if not bucket:
        return
    # 清空一个 bucket 的相关逻辑，但是要慎重使用，一般除了 本地Debug 之外，不进行这个操作
    clear_related_buckets(bucket)

    # after_record_created 中的一些数据统计清理
    hdel('_bucket_usage', bucket)
    hdel('_records_count', bucket)

    if delete_files:
        # 删除对应的文件
        loop_records_for_bucket(bucket, storage.when_record_deleted)

    # at last
    hclear(bucket)
    remove_bucket_from_buckets(bucket)