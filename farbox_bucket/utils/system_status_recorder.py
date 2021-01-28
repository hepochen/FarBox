# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.ssdb_utils import hset, hget, hscan
import datetime
import time




class record_system_timed_status(object):
    """
    @record_system_timed_status(field='??')
    """
    def __init__(self, field):
        self.field = field

    def __call__(self, func):
        def _func(*args, **kwargs):
            t1 = time.time()
            result = func(*args, **kwargs)
            try:
                seconds_cost = str(time.time() - t1)
                key = '%s_%s' % (int(t1*1000), self.field)
                hset('_system_recorder', key=key, value=seconds_cost)
            except:
                pass
            return result
        return _func



def get_system_timed_records():
    raw_records = hscan('_system_recorder', limit=1000, reverse_scan=True)
    records = []
    for record_id, seconds_cost in raw_records:
        if '_' not in record_id:
            continue
        timestamp, action_name = record_id.split('_', 1)
        try:
            timestamp = int(timestamp)/1000.
        except:
            continue
        date = datetime.datetime.utcfromtimestamp(timestamp)
        date = date.strftime('%Y-%m-%d %H:%M:%S')
        record = '%s UTC %s costs %s' % (date, action_name, seconds_cost)
        records.append(record)
    return records
