# coding: utf8
from farbox_bucket.server.web_app import app

from farbox_bucket.bucket.web_api.handler import FarBoxBucketMessageAPIHandler


farbox_bucket_message_api_handler = FarBoxBucketMessageAPIHandler()

@app.route('/farbox_bucket_message_api', methods=['GET', 'POST'])
def message_handler():
    response = farbox_bucket_message_api_handler.return_response()
    return response

