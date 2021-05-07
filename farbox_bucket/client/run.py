#coding: utf8
import os
import time
import gc
from farbox_bucket import settings
from farbox_bucket.utils.encrypt.key_encrypt import is_valid_private_key
from farbox_bucket.client.sync import sync_to_farbox
from farbox_bucket.client.sync_from import sync_from_farbox
from farbox_bucket.utils.error import print_error
from farbox_bucket.utils.file_version import create_file_version


# python -m farbox_bucket.client.run


def _get_value_from_env(key):
    key = key.strip()
    value = os.environ.get(key) or os.environ.get(key.upper())
    if not value and "_" in key:
        key = key.split("_")[0]
        value = os.environ.get(key) or os.environ.get(key.upper())
    return value



def run_client(node=None, root=None, private_key=None):
    # 同步的策略，先将本地的内容同步到服务端，再从服务端同步一次回来
    settings.DEBUG = True
    node = node or _get_value_from_env("node")
    root = root or _get_value_from_env("root") or "/mt/data"
    private_key = private_key or _get_value_from_env("private_key")
    if not node or not root or not private_key:
        print("node & root & private_key required")
        return
    if not os.path.isdir(root):
        print("root is not a dir")
        return
    if "/" in private_key and os.path.isfile(private_key):
        # private key is a filepath
        with open(private_key, "rb") as f:
            private_key = f.read()
    if not is_valid_private_key(private_key):
        print("private key invalid")
        return
    # sync to FarBox server first
    #print("sync_to_farbox...")
    sync_to_farbox(node=node, root=root, private_key=private_key)
    # sync back from FarBox Server
    #print("sync_from_farbox...")
    # 利用 before_file_sync_func 进行历史版本的存储，进一步保证数据的安全
    sync_from_farbox(node=node, root=root, private_key=private_key, before_file_sync_func=create_file_version)


def keep_running_client(node=None, root=None, private_key=None):
    # run_client per 30 seconds, and keep going...
    print("keep running client to sync with FarBox...")
    while True:
        try:
            run_client(node=node, root=root, private_key=private_key)
        except:
            try:
                print_error()
            except:
                pass
        finally:
            #print("sleeping 60 seconds")
            time.sleep(60)
            gc.collect()


if __name__ == "__main__":
    keep_running_client()