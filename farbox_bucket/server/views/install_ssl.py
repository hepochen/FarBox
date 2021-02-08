# coding: utf8
from __future__ import absolute_import
from farbox_bucket.server.web_app import app
from flask import abort, request
from farbox_bucket.server.utils.response import send_plain_text
from farbox_bucket.bucket.domain.utils import get_bucket_from_domain
from farbox_bucket.bucket.domain.ssl_utils import get_ssl_cert_for_domain
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request



@app.route('/_system/install_ssl', methods=['POST', 'GET'])
@app.route('/_system/install_ssl/<domain>', methods=['POST', 'GET'])
def install_ssl(domain=''):
    set_not_cache_current_request()
    domain = domain or request.values.get('domain', '').lower().strip()
    if ':' in domain:
        domain = domain.split(':')[0]
    if not request.host.startswith('127.0.0.1'):
        abort(404, 'should be localhost')
    if request.remote_addr and request.remote_addr != '127.0.0.1':
        abort(404, 'outside error')

    bucket = get_bucket_from_domain(domain)
    if not bucket:
        abort(404, 'bucket is not found')

    cert_doc = get_ssl_cert_for_domain(domain)

    ssl_key = cert_doc.get('ssl_key')
    ssl_cert = cert_doc.get('ssl_cert')
    if ssl_key and ssl_cert:
        return send_plain_text('%s,%s' % (ssl_key, ssl_cert))
    else:
        return ','


