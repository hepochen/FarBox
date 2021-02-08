# coding: utf8
from farbox_bucket.utils.encrypt.key_encrypt import create_private_public_keys


def get_private_key_on_server_side():
    private_key, public_key = create_private_public_keys()
    return private_key
