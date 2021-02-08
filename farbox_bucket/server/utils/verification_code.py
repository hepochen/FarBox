# coding: utf8
import uuid
import random
import os
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shortuuid import ShortUUID
from flask import request, Response
from farbox_bucket.utils import smart_str
from farbox_bucket.utils.memcache import cache_client
from farbox_bucket.settings import server_secret_key
from farbox_bucket.server.utils.cookie import set_cookie, get_cookie
from farbox_bucket.server.static.static_render import static_folder_path
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request
from farbox_bucket.server.web_app import app

v_shortuuid = ShortUUID('ABCDEFGHJKMNPQRSTUVWXY345679')


text_font = None
def get_text_font(font_size=21):
    global text_font
    if text_font is None:
        font_path = os.path.join(static_folder_path, 'gfonts/Lato_400_normal.ttf')
        if os.path.isfile(font_path):
            font = ImageFont.truetype(font_path, size=font_size)
        else:
            font = ImageFont.load_default()
        text_font = font
    return text_font


def generate_chars(key=None, length=4):
    if not key:
        key = uuid.uuid1().hex
    v_to_uuid = smart_str(key) + smart_str(server_secret_key)
    result = v_shortuuid.uuid(v_to_uuid)
    return result[:length]



def chars_to_image(key=None, im_size=(100,30), bg_color=(255, 255, 255), font_color=(193, 0, 30), font_size=21,):
    width, height = im_size
    chars = generate_chars(key)
    chars_to_draw = ' '.join(list(chars))

    im = Image.new('RGB', im_size, bg_color)
    im_draw = ImageDraw.Draw(im)

    def get_random_dot():
        x, y = random.randint(0, width), random.randint(0, height)
        dot = (x, y)
        return dot

    # draw lines
    for i in range(random.randint(1, 2)):
        xy = [get_random_dot(), get_random_dot()]
        im_draw.line(xy, fill=(190,190,190))

    # draw random points
    k = min(width, height)
    ws = random.sample(range(width), k)
    hs = random.sample(range(0, height), k)
    for i in range(k):
        im_draw.point([ws[i], hs[i]], fill=(10,100,100))

    # draw text now
    font = get_text_font(font_size=font_size)
    s_width, s_height = font.getsize(chars_to_draw)
    xy = ((width - s_width) / 2 - 5, (height - s_height) / 2 - 5)
    im_draw.text(xy, chars_to_draw, font=font, fill=font_color)

    # 图形扭曲参数
    params = [1 - float(random.randint(1, 2)) / 100, 0, 0, 0, 1 - float(random.randint(1, 10)) / 100,
              float(random.randint(1, 2)) / 200, 0.001, float(random.randint(1, 2)) / 300]
    im = im.transform(im_size, Image.PERSPECTIVE, params)  # 创建扭曲
    im = im.filter(ImageFilter.EDGE_ENHANCE)  # 滤镜，边界加强（阈值更大）
    return im



def image_to_bytes(im, im_format='PNG'):
    f = BytesIO()
    if im_format.lower() != 'png':
        im_format = 'JPEG'
    else:
        im_format = 'PNG'
    im.save(f, format=im_format)
    bytes_content = f.getvalue()
    return bytes_content


def image_to_base64(im, im_format='PNG', as_url=False):
    f = BytesIO()
    if im_format.lower() != 'png':
        im_format = 'JPEG'
        url_prefix = 'data:image/jpeg'
    else:
        im_format = 'PNG'
        url_prefix = 'data:image/png'
    im.save(f, format=im_format)
    b64_content = base64.b64encode(f.getvalue())
    if as_url:
        b64_content = '%s;base64,%s' % (url_prefix, b64_content)
    return smart_str(b64_content)



############################################################################################################


def is_verification_code_correct():
    code_id = get_cookie('verification_code')
    cache_key = 'vcode_%s'%code_id
    vid = cache_client.get(cache_key)
    vid_in_request = get_cookie('vid') or '1'
    if vid != vid_in_request:
        return False
    chars = generate_chars(code_id)
    verification_code = request.values.get('verification_code', '').strip().lower()
    if chars.lower() == verification_code:
        cache_client.delete(cache_key)
        return True
    else:
        return False


# todo 限制访客的请求数，避免被攻击
@app.route('/service/verification_code', methods=['POST', 'GET'])
def show_verification_code_by_url():
    set_not_cache_current_request()
    code_id = uuid.uuid1().hex
    set_cookie('verification_code', code_id)
    vid = get_cookie('vid') or '1'
    cache_client.set('vcode_%s'%code_id, vid, expiration=10*60)
    im = chars_to_image(key=code_id)
    im_content = image_to_bytes(im, im_format='PNG')
    response = Response(im_content, mimetype='image/png')
    return response



