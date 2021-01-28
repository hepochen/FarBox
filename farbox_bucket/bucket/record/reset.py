# coding: utf8
from .get.helper import loop_records_for_bucket
from farbox_bucket.bucket.defaults import zero_ids
from farbox_bucket.utils.ssdb_utils import hdel, hdel_many
from farbox_bucket.bucket.utils import get_bucket_files_info
from farbox_bucket.bucket.record.get.path_related import get_record_id_by_path
from farbox_bucket.bucket.record.related.for_all import update_path_related_when_record_changed



def reset_related_records(bucket):
    def reset_record(record):
        record_id = record.get('_id')
        update_path_related_when_record_changed(bucket=bucket, record_id=record_id, record_data=record)
    loop_records_for_bucket(bucket, func_for_record=reset_record)


