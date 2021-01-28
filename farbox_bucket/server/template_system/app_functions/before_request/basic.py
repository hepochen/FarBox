# coding: utf8
from flask import request

def basic_before_request():
    if request.environ.get('HTTP_X_PROTOCOL') == 'https': # ssl
        request.url = request.url.replace('http://', 'https://', 1)
        request.url_root = request.url_root.replace('http://', 'https://', 1)