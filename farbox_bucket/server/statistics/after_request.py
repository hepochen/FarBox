# coding: utf8
from gevent import spawn
from farbox_bucket.settings import sentry_client
from .post_visits import update_post_visits_for_response
from .usage_collect import update_usage_statistics

def after_request_func_for_statistics(response):
    try:
        update_post_visits_for_response(response) # 因为调用了 request/g，不能放在 spawn 中处理
    except:
        if sentry_client: sentry_client.captureException()

    update_usage_statistics(response)

    return response

