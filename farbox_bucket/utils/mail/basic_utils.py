#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import email_re, string_types

def pure_email_address(address, check=False):
    #name <xxxx>  -> xxxx & 小写处理
    if not address:
        return
    if isinstance(address, (list, tuple)) and len(address) == 1:
        address = address[0]
    if isinstance(address, string_types):
        address = address.split('<', 1)[-1].strip('<>').strip().lower()
        address = address.replace('%40', '@')  # for URL
    if check:
        if not is_email_address(address):
            return
    return address


def is_email_address(email):
    if isinstance(email, string_types):
        email = email.strip()
        if email:
            return bool(email_re.match(email))
    return False


def get_valid_addresses(addresses, max_size=None):
    if isinstance(addresses, string_types): # 单一的一个邮箱地址
        return pure_email_address(addresses)
    if not isinstance(addresses, (tuple, list)): # 不支持的类型
        return []
    result = []
    for address in addresses:
        if is_email_address(address):
            address = pure_email_address(address)
            if address not in result:
                result.append(address)
    if max_size and isinstance(max_size, int):
        result = result[:max_size]
    return result


