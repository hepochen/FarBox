#coding: utf8
import os, struct
import io
try:
    from pgmagick import Blob, Image
except:
    Blob, Image = None, None

def get_image_type(content_or_part, is_file=False):
    if is_file:
        if not os.path.exists(content_or_part):
            return 'unknown'
        else:
            with open(content_or_part, 'rb') as f:
                content_or_part = f.read(99)
    if len(content_or_part) < 8:
        return 'unknown'
    marker = content_or_part[:8]
    if marker.startswith("\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"):
        return 'PNG'
    elif marker.startswith('\x89PNG\r\n\x1a'):
        return 'PNG'
    elif marker.startswith('\x89PNG'):
        return 'PNG'
    elif marker.startswith('GIF'):
        return 'GIF'
    elif marker.startswith("\xFF\xD8\xFF"):
        return 'JPEG'
    elif marker.startswith('BM'):
        return 'BMP'
    else:
        return 'unknown'




def get_im_size(im):
    size = im.size()
    return size.width(), size.height()


def get_im(content):
    if hasattr(content, 'read'):
        content = content.read()
    if not content:
        return
    else:
        try:
            f = Blob(content)
            return Image(f)
        except:
            return

def get_quality(im, quality=None):
    default_quality = 91
    if im.attribute('JPEG-Quality').isalnum():
        if quality:
            quality = min(quality, int(im.attribute('JPEG-Quality')))
        else:
            quality = int(im.attribute('JPEG-Quality'))
    else:
        quality = default_quality
    return quality


def get_jpg_image_data(im, quality=90):
    # quality
    im.profile("*", Blob()) # 清掉exif信息
    im.quality(quality)
    f = Blob()
    im.write(f, 'jpg')
    return getattr(f, 'data')



def fast_get_image_size(raw_data):
    """
    Return (width, height) for a given img file content - no external
    dependencies except the os and struct modules from core
    """
    size = len(raw_data)
    data = raw_data[:25]
    input_io = io.BytesIO(data)
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # GIFs
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        # PNGs
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # older PNGs?
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)
    elif (size >= 2) and data.startswith('\377\330'):
        # JPEG
        input_io.seek(0)
        input_io.read(2)
        b = input_io.read(1)
        try:
            w = ''
            h = ''
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = input_io.read(1)
                while (ord(b) == 0xFF): b = input_io.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    input_io.read(3)
                    h, w = struct.unpack(">HH", input_io.read(4))
                    break
                else:
                    input_io.read(int(struct.unpack(">H", input_io.read(2))[0])-2)
                b = input_io.read(1)
            width = int(w)
            height = int(h)
        except Exception as e:
            #print 'get size error'
            return 0, 0
    else:
        # print "Sorry, don't know how to get information from this file %s" % file_path
        return 0, 0
    if width < 0 or height<0:
        return 0, 0
    else:
        return width, height