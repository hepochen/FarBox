# coding: utf8
from __future__ import absolute_import
from io import BytesIO
import zlib
#from gzip import GzipFile
from base64 import b64decode, b64encode


def gzip_content(content, base64=False):
    if isinstance(content, unicode):
        content = content.encode('utf8')
    zipped_content = zlib.compress(content)
    if base64:
        zipped_content = b64encode(zipped_content)
    return zipped_content


def ungzip_content(raw_content, base64=False):
    if base64:
        raw_content = b64decode(raw_content)
    if isinstance(raw_content, unicode):
        raw_content = raw_content.encode('utf8')
    original_size = len(raw_content)
    f = BytesIO(raw_content)
    #z = zlib.decompressobj(15 + 16) # zlib.MAX_WBITS == 15
    z = zlib.decompressobj()
    total_size = 0
    content = ''
    while True:
        buf = z.unconsumed_tail
        if buf == "":
            buf = f.read(1024)
            if buf == "":
                break
        got = z.decompress(buf, 4096)
        if got == "":
            break
        content += got
        total_size += len(got)
        if total_size > 50*original_size:
            # this is boom
            return ''
    return content