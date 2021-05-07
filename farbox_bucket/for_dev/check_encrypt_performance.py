# coding: utf8
from farbox_bucket.utils.encrypt.des_encrypt import encrypt_des, decrypt_des
from farbox_bucket.utils.encrypt.aes_encrypt import encrypt_aes, decrypt_aes
import time

content = 'hello world this is test'
password = 'passwordhere'

def check_encrypt_performance():
    t1 = time.time()
    for i in range(10000):
        c = encrypt_aes(content, password, encode_type='raw')
        d = decrypt_aes(c, password, encode_type='raw')
    print("original_size is %s, encrypted_content size is %s, is equal: %s" % (len(content), len(c), d==content))
    print("encrypt & decrypt costs %s seconds" % (time.time() - t1))



    t1 = time.time()
    for i in range(10000):
        c = encrypt_des(content, password, )
        d = decrypt_des(c, password, )
    print("encrypt & decrypt costs %s seconds, in base64 " % (time.time() - t1))



if __name__ == "__main__":
    check_encrypt_performance()