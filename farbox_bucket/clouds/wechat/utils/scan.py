#coding: utf8
from __future__ import absolute_import
from configs.database import log_db
import time, datetime
from pymongo.errors import DuplicateKeyError



def get_new_scan_id():
    # 自增式的整数id
    try_times = 0
    try:
        max_one = log_db.we_scan.find().sort('_id', -1).next()
        scan_id = max_one['_id']+1
    except StopIteration:
        scan_id = 1 # 第一次
    return scan_id


def _save_scan_doc(doc):
    if not isinstance(doc, dict):
        doc = dict(just_value = doc)
    scan_id = get_new_scan_id()
    doc['_id'] = scan_id
    doc['scan_date'] = datetime.datetime.utcnow()
    log_db.we_scan.insert(doc) # 使用insert，这样如果有重复的，会触发错误
    return scan_id # 返回id，可以让后续的程序进行调用

def save_scan_doc(doc):
    # 可能几乎同时产生的scan_id, 会有key重复的问题，最多重试10次
    try_times = 0
    while try_times < 10:
        try:
            scan_id = _save_scan_doc(doc)
            return scan_id
        except DuplicateKeyError:
            pass
        try_times += 1
        time.sleep(0.3)


def get_scan_doc(scan_id):
    try:
        scan_id = int(scan_id) # 必须是整数
    except:
        return # ignore
    doc = log_db.we_scan.find_one(scan_id)
    if doc:
        if 'just_value' in doc:
            return doc['just_value']
        else:
            return doc
    else:
        return None