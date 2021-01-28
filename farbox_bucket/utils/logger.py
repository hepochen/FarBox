#coding: utf8
from __future__ import absolute_import
import logging


cached_file_loggers = {}

def get_file_logger(name):
    cached_logger = cached_file_loggers.get(name)
    if cached_logger:
        return cached_logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # create a file handler
    try:
        handler = logging.FileHandler('/var/log/%s.log'%name)
    except:
        handler = logging.FileHandler('/tmp/log_%s.log' % name)
    handler.setLevel(logging.INFO)
    # create a logging format
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(handler)
    cached_file_loggers[name] = logger
    return logger