# coding: utf8
from farbox_bucket.bucket.record.utils import get_data_type
from .for_posts import update_post_tags_words_info


def update_tags_info_for_posts(bucket, record_data):
    # store the files info

    doc_type = get_data_type(record_data)
    if doc_type == 'post':
        update_post_tags_words_info(bucket=bucket, record_data=record_data)