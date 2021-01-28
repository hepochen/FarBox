#coding: utf8
from __future__ import absolute_import
from flask import make_response, Response
from farbox_bucket.utils.data import json_dumps

STATUS_MESSAGES = {
    200: 'ok',
    500: 'Server Error',
    503: 'Wait for a Moment, and Try Again.',
    400: 'Bad Request',
    401: 'Auth error.',
    404: 'Page not Found or this Request is not Allowed',
}


def jsonify(data):
    try:
        data = json_dumps(data, indent=4)
    except:
        data = json_dumps(dict(error='json_error'))
    response = Response(data, mimetype='application/json')
    return response



def json_with_status_code(code, message=''):
    message = message or STATUS_MESSAGES.get(code, '')
    result = dict(code=code, message=message)
    response = make_response(jsonify(result))
    response.status_code = code
    return response
