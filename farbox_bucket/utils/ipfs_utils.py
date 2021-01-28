# coding: utf8
import os
import time
from farbox_bucket.utils import smart_str
from farbox_bucket.utils.path import delete_file
from farbox_bucket.utils.encrypt.aes_encrypt import encrypt_file as _encrypt_file
import tempfile

def run_command(command):
    try:
        f = os.popen(command)
        result = f.read().strip()
        f.close()
        return result
    except:
        return None


current_ipfs_bin_path = None
def get_ipfs_bin_path():
    global current_ipfs_bin_path
    if current_ipfs_bin_path is not None:
        return current_ipfs_bin_path
    ipfs_bin_paths = [
        '/usr/bin/ipfs',
        '/usr/local/bin/ipfs',
        '/usr/local/ipfs',
    ]
    for bin_filepath in ipfs_bin_paths:
        if os.path.isfile(bin_filepath):
            current_ipfs_bin_path = bin_filepath
            return bin_filepath
    current_ipfs_bin_path = ''  # at last, cache it
    return ''

def run_ipfs_cmd(cmd, tried=0):
    raw_cmd = cmd
    cmd = cmd.strip()
    if cmd.startswith('ipfs '):
        cmd = cmd.replace('ipfs ', '', 1)
    bin_path = get_ipfs_bin_path()
    if not bin_path:
        return
    full_cmd = '%s %s' % (bin_path, cmd)
    result = run_command(full_cmd)
    tried += 1
    if result and 'repo.lock failed' in result and tried <= 5: # retry
        time.sleep(0.5)
        return run_ipfs_cmd(raw_cmd, tried=tried)
    return result


def add_filepath_to_ipfs(filepath, only_hash=False):
    if not os.path.isfile(filepath):
        return
    only_hash = only_hash
    if only_hash:
        cmd = 'ipfs add --quieter --only-hash "%s"' % filepath
    else:
        cmd = 'ipfs add --quieter "%s"' % filepath
    cmd = smart_str(cmd)
    result = run_ipfs_cmd(cmd)
    if result:
        result = result.strip()
        if not result.startswith('Qm'): # not a valid ipfs hash value
            return
    return result


def just_get_ipfs_hash_from_filepath(filepath):
    if not os.path.isfile(filepath):
        return
    ipfs_hash = add_filepath_to_ipfs(filepath, only_hash=True)
    return ipfs_hash



def get_ipfs_hash_from_filepath(filepath, encrypt_key=None):
    # 如果指定 encrypt_key，那么， 就是进行加密后的处理
    if not os.path.isfile(filepath):
        return
    filepath_for_ipfs = filepath
    to_delete_tmp_file = False
    if encrypt_key:
        filepath_for_ipfs = encrypt_file(filepath, encrypt_key=encrypt_key)
        to_delete_tmp_file = True
    ipfs_hash = just_get_ipfs_hash_from_filepath(filepath)
    if to_delete_tmp_file: # 删除临时文件
        delete_file(filepath_for_ipfs)
    return ipfs_hash




def remove_hash_from_ipfs(ipfs_hash):
    # 实际上是移除 pin 的逻辑而已，并不能真正意义上进行删除
    if not ipfs_hash.startswith('Qm'):
        return
    cmd = 'ipfs pin rm %s' % ipfs_hash
    run_ipfs_cmd(cmd)



def clear_ipfs():
    run_ipfs_cmd('ipfs repo gc')




def encrypt_file(original_filepath, encrypt_key):
    # 会创建一个临时文件
    if not original_filepath:
        return
    if not os.path.isfile(original_filepath):
        return
    ext = os.path.splitext(original_filepath)[-1]
    tmp_filepath = tempfile.mktemp(suffix=ext)
    try:
        encrypt_key = encrypt_key.strip()
        _encrypt_file(original_filepath, key=encrypt_key, out_filepath=tmp_filepath)
        #if not test_encrypt_file(original_filepath):
        #    print('\n\n\n\n\n\n\n\n%s test error\n\n\n\n\n\n\n\n' % original_filepath)
    except:
        return
    return tmp_filepath



# todo keep connected

def keep_connected(remote_address, bin_path=None, api_client=None):
    pass