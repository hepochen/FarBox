# coding: utf8
from __future__ import absolute_import
from jinja2.runtime import Context
from flask import g, request
import re

from farbox_bucket.bucket.defaults import zero_id_for_finder

from farbox_bucket.bucket.record.get.get import get_records_for_bucket


def get_records_for_request_resolver(key):
    if not hasattr(g, 'cached_records_for_resolver'):
        g.cached_records_for_resolver = {}

    key = key.lower().strip()
    if key in g.cached_records_for_resolver: # cached value
        return g.cached_records_for_resolver[key]

    if not re.match('r?records(_\d+)?$', key):
        return None

    bucket = getattr(g, 'bucket', None)
    if not bucket:
        return []

    if key.startswith('rrecords'):
        reverse_scan =  True
    else:
        reverse_scan = False

    if '_' in key:
        per_page = key.split('_')[-1]
        if not per_page:
            per_page = 100 # default value
        else:
            per_page = int(per_page)
    else:
        per_page = 100

    if per_page < 1:
        per_page = 1
    if per_page > 1000: # max_value
        per_page = 1000

    icursor = request.values.get('icursor')
    cursor = request.values.get('cursor') or icursor
    if not reverse_scan:
        start_record_id = cursor or zero_id_for_finder
        end_record_id = ''
    else:
        start_record_id = cursor or ''
        end_record_id = zero_id_for_finder

    includes_start_record_id = bool(icursor)

    records = get_records_for_bucket(bucket, start_record_id=start_record_id,
                                     end_record_id=end_record_id,
                                     limit=per_page,
                                     reverse_scan=reverse_scan,
                                     includes_start_record_id=includes_start_record_id,
                                     )

    g.cached_records_for_resolver[key] = records

    return records
