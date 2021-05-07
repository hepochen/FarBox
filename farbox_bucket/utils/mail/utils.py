#coding: utf8
from __future__ import absolute_import
import boto3

from farbox_bucket.utils import smart_str, smart_unicode
from farbox_bucket.utils.mail.basic_utils import pure_email_address, is_email_address, get_valid_addresses


#https://stackoverflow.com/questions/62757921/is-aws-boto-python-supporting-ses-signature-version-4
# https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html


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


# us-east-1 Region

def send_email_by_ses(from_address, to_address,  content, ses_id, ses_key, subject='', region="us-east-1"):
    client = boto3.client("ses", aws_access_key_id=ses_id, aws_secret_access_key=ses_key, region_name=region or "us-east-1")
    if not isinstance(to_address, (list, tuple)):
        to_address = [to_address]

    addresses = get_valid_addresses(to_address)
    if not addresses:
        return

    result = client.send_email(
        Source = from_address,
        Destination = {
            "ToAddresses": addresses
        },
        Message = {
            "Subject": {
                "Data": subject or "",
            },
            "Body": {
                "Html": {
                    "Data": content
                }
            }
        }
    )
    # {u'SendEmailResponse': {u'ResponseMetadata': {u'RequestId': u'436aa914-56e2-11e6-842f-575aa5bf2b20'},
    # u'SendEmailResult': {u'MessageId': u'010001563f7e2795-b2c75be1-7bc4-4511-be81-e9ab0d3329e0-000000'}}}
    try:
        #message_id = result['SendEmailResponse']['SendEmailResult']['MessageId']
        message_id = result["MessageId"]
        return message_id
    except:
        return result



def send_email_by_amazon(from_address, to_address, content,  ses_id, ses_key, subject="", raw=False):
    # 对 SES 的直接调用
    if not ses_id or not ses_key:
        return None
    message_id = send_email_by_ses(from_address=from_address, to_address=to_address, content=content, subject=subject, ses_id=ses_id, ses_key=ses_key)

    return message_id







