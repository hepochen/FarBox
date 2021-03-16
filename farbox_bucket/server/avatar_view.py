#coding: utf8
from flask import Response, abort
import base64, time
from farbox_bucket.server.web_app import app
from farbox_bucket.utils.ssdb_utils import hget, hset, hdel
from farbox_bucket.server.utils.response import get_304_response, is_doc_modified, set_304_response_for_doc
from farbox_bucket.server.static.static_render import send_static_file

from .avatar import get_avatar_id, get_gavatar_image_content


@app.route('/service/avatar/<avatar_id>')
def show_avatar(avatar_id):
    avatar_id = get_avatar_id(avatar_id)
    avatar_doc = hget('_avatar', avatar_id)
    now = time.time()
    if avatar_doc:
        avatar_date = avatar_doc.get('date')
        avatar_image_content = avatar_doc.get('content')
        to_clear = False
        if not avatar_date:
            to_clear = True
        elif (now-avatar_date) > 5*24*60*60: # 5days
            to_clear = True
        elif (now - avatar_date) > 1 * 24 * 60 * 60 and not avatar_image_content: # 1day for empty avatar image
            to_clear = True
        if to_clear:
            # avatar_doc 缓存 5 天
            hdel('_avatar', avatar_id)
            avatar_doc = None
    if not avatar_doc:
        avatar_image_content = get_gavatar_image_content(avatar_id) or ''
        if avatar_image_content:
            avatar_image_content = base64.b64encode(avatar_image_content)
        avatar_doc = dict(
            date = now,
            content = avatar_image_content
        )
        hset('_avatar', avatar_id, avatar_doc)

    if not is_doc_modified(avatar_doc, date_field='date'):
        return get_304_response()
    else:
        avatar_image_content = avatar_doc.get('content') or ''
        if avatar_image_content:
            avatar_image_content = base64.b64decode(avatar_image_content)
            response = Response(avatar_image_content, mimetype='image/png')
            set_304_response_for_doc(avatar_doc, response, date_field='date')
            return response
        else:
            # 默认的 url
            r_response = send_static_file('defaults/avatar.png')
            if r_response:
                return r_response
    # at last
    abort(404)
