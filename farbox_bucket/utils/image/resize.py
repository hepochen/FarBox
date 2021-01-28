#coding:utf8
try:
    from pgmagick import Blob, Geometry, Image, CompositeOperator as co
except:
    Blob, Geometry, Image, co = None, None, None, None
from .utils import get_im_size

def safe_size(size):
    """size:int or None"""
    if size is None:
        return
    try:
        size = int(size)
    except (TypeError, ValueError):
        return
    allowed = [40, 80, 120, 160, 214, 240, 320, 428, 480, 640, 960, 1280, 1560]
    for i in range(1, len(allowed)):
        standard_small = allowed[i-1]
        standard_big = allowed[i]
        if standard_big > size:
            if abs(standard_big-size) > abs(standard_small-size):
                return standard_small
            else:
                return standard_big
    return allowed[-1]



def list_to_size(ls):
    ls = [int(i) for i in ls]
    return '%sx%s'%(ls[0], ls[1])



def resize_image(im, width=None, height=None, fixed=False, quality=86, image_type='image/jpeg', degrees=0):
    """
    返回的是blob类型的，取data
    """
    w, h = get_im_size(im) #w, h  原始尺寸

    # size means what u want
    if height is None and fixed:
        mode = 'fixed_width'
        times = w/float(width)
        size = [w/times, h/times]
    elif width is None and fixed:
        mode = 'fixed_height'
        times = h/float(height)
        size = [w/times, h/times]
    elif height is None and width is None: # 必须要指定 width or height
        raise Exception
    else:
        width = width or w
        height = height or h
        size = [width, height]
        if fixed: mode = 'fixed_both'
        else: mode = 'auto'

    if mode == 'fixed_both':
        # get the pre_thumbnail then cut!
        m = max(size[0]/float(w), size[1]/float(h)) #max_thumbnail_rate  不裁剪的缩放比
        if m> 1: m=1
        im.scale(list_to_size([w*m, h*m]))
        n_w, n_h = get_im_size(im)
        size= [min(size[0],n_w), min(size[1], n_h)] # # 最后的图片尺寸 in case, the image size is not big enough

        width, height = size
        left = int((n_w-width)/2.0)
        top = int((n_h-height)/2.0)
        box = Geometry(width, height, left, top)
        im.crop(box)
    else:
        size = [min(size[0], w), min(size[1], h)]
        im.scale(list_to_size(size))

    if degrees and isinstance(degrees, (int, float)): # 旋转正向
        im.rotate(int(degrees))

    # quality
    im.profile("*", Blob()) # 清掉exif信息
    im.quality(quality)
    f = Blob()
    if image_type in ['image/png', 'png']:
        image_type = 'png'
    elif image_type in ['webp', 'image/webp']:
        image_type = 'webp'
    else:
        image_type = 'jpg'
    if image_type in ['jpg', 'jpeg']:
        # 填充白色背景
        base_im = Image(im.size(), '#ffffff')
        base_im.composite(im, 0, 0, co.OverCompositeOp)
        im = base_im
    im.write(f, image_type)
    return getattr(f, 'data')



def can_resize_by_system():
    if Blob:
        return True
    else:
        return False



def __main__():
    pass


if __name__ == "__main__":
    __main__()