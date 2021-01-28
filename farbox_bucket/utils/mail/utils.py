#coding: utf8
from __future__ import absolute_import
import boto, datetime, requests

from farbox_bucket.utils import smart_str, smart_unicode
from farbox_bucket.utils.mail.basic_utils import pure_email_address, is_email_address, get_valid_addresses



def get_mail_server_domain(address):
    if not is_email_address(address):
        return
    domain = address.split('@')[-1].lower().strip()
    return domain



def get_address_and_sub_info_from_address(address):
    # 解析 a+subinfo@domain.com 这种格式的邮箱地址
    parts = address.split('@', 1)
    prefix, suffix = parts
    if '+' not in prefix:
        sub_info = None
    else:
        prefix, sub_info = prefix.split('+', 1)
    address = '%s@%s' % (prefix, suffix)
    address = address.lower()
    return address, sub_info



def raw_send_email_by_ses(from_address, to_address, content, ses_id, ses_key, subject=None):
    ses_connection = boto.connect_ses(ses_id, ses_key)
    if not isinstance(to_address, (list, tuple)):
        to_address = [to_address]
    addresses = get_valid_addresses(to_address)
    if not addresses:
        return
    if isinstance(content, unicode):
        content = content.encode('utf8')
    result = ses_connection.send_raw_email(content, source=from_address, destinations=addresses)
    try:
        message_id = result['SendRawEmailResponse']['SendRawEmailResult']['MessageId']
        return message_id
    except:
        return result


def send_email_by_ses(from_address, to_address,  content, ses_id, ses_key, subject=''):
    ses_connection = boto.connect_ses(ses_id, ses_key)
    if not isinstance(to_address, (list, tuple)):
        to_address = [to_address]

    addresses = get_valid_addresses(to_address)
    if not addresses:
        return

    result = ses_connection.send_email(
        source=from_address,
        subject=subject,
        body = '',
        html_body=content,
        to_addresses= addresses
    )
    # {u'SendEmailResponse': {u'ResponseMetadata': {u'RequestId': u'436aa914-56e2-11e6-842f-575aa5bf2b20'},
    # u'SendEmailResult': {u'MessageId': u'010001563f7e2795-b2c75be1-7bc4-4511-be81-e9ab0d3329e0-000000'}}}
    try:
        message_id = result['SendEmailResponse']['SendEmailResult']['MessageId']
        return message_id
    except:
        return result



def send_email_by_amazon(from_address, to_address, content,  ses_id, ses_key, subject=None, raw=False):
    # 对 SES 的直接调用
    if not ses_id or not ses_key:
        return None
    if raw:
        func = raw_send_email_by_ses
    else:
        func = send_email_by_ses
    message_id = func(from_address=from_address, to_address=to_address, content=content, subject=subject, ses_id=ses_id, ses_key=ses_key)

    return message_id



def send_email_by_mailgun(from_address, to_address, subject, html_content, api_host, api_key):
    if not isinstance(to_address, (list, tuple)):
        to_address = [to_address]

    addresses = get_valid_addresses(to_address)
    if not addresses:
        return

    response = requests.post(
        api_host,
        auth=("api", api_key),
        data={"from": from_address,
              "to": addresses,
              "subject": smart_str(subject),
              "html": smart_str(html_content)}
    )
    # {u'id': u'<20160731050105.19538.10328.09D720EA@farbox.com>',
    # u'message': u'Queued. Thank you.'}
    try:
        result = response.json()
        message_id = result['id']
        message_id = message_id.lstrip('<').rstrip('>')
        return message_id
    except:
        return response







