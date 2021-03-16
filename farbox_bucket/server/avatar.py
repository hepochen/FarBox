# coding: utf8
import requests
from farbox_bucket.utils import get_md5, string_types
from farbox_bucket.utils.ssdb_utils import hexists


def get_avatar_id(email): # 根据邮件地址，或者对应的m5值作为avatar_id
    if isinstance(email, string_types) and email:
        email = email.lower().strip()
        if '@' in email:
            return get_md5(email)
        else:
            return email
    return None # if not



def get_gavatar_image_content(email):
    avatar_id = get_avatar_id(email)
    gravatar_url = 'https://en.gravatar.com/%s.json' % avatar_id
    response = requests.get(gravatar_url, verify=False, timeout=10)
    if response.status_code != 200:
        return ''
    response_info = response.json()
    gravatar_image_url = response_info['entry'][0]['thumbnailUrl']
    if gravatar_image_url:
        try:
            image_response = requests.get(gravatar_image_url, timeout=10, verify=False)
            if image_response.status_code > 300:
                return ''  # ignore
            else:
                return image_response.content
        except:
            return ''

def has_avatar(email_md5):
    if '@' in email_md5:
        email_md5 = get_avatar_id(email_md5)
    if not isinstance(email_md5, string_types):
        return False
    if len(email_md5) > 64:
        return False
    email_md5 = email_md5.lower().strip()
    return hexists('_avatar', email_md5)


def get_avatar_url(email):
    avatar_id = get_avatar_id(email)
    url = '/service/avatar/%s' % avatar_id
    return url








