# coding: utf8
from farbox_bucket.bucket.record.utils import get_data_type
from .for_files import update_bucket_files_info
from .for_posts import update_post_tags_words_info


def update_files_and_tags(bucket, record_data):
    # store the files info
    update_bucket_files_info(bucket)

    doc_type = get_data_type(record_data)
    if doc_type == 'post':
        update_post_tags_words_info(bucket=bucket, record_data=record_data)