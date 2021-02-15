# coding: utf8
import re
from farbox_bucket.utils import smart_unicode
from farbox_bucket.utils.path import get_just_name
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.bucket.utils import get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.server.template_system.api_template_render import render_api_template
from farbox_bucket.server.template_system.namespace.data import Data
from farbox_bucket.server.utils.request_path import get_request_path


def show_albums_as_sub_site():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return
    request_path = get_request_path().strip("/")
    if not re.match("album(/|$)", request_path):
        return
    if "." in request_path and guess_type(request_path, default_type="").startswith("image/"):
        # 可能是直接的图片地址，避免被整个 album 给拦截了
        return
    site_configs = get_bucket_site_configs(bucket)
    albums_root = smart_unicode(site_configs.get("albums_root", ""))
    if not albums_root:
        return
    albums_root = albums_root.strip("/") #todo 允许直接设定 / ？
    albums_home_sort = site_configs.get("albums_home_sort", "-date")
    album_items_sort = site_configs.get("album_items_sort", "-date")

    page_title = site_configs.get("albums_title") or get_just_name(albums_root, for_folder=True)

    if re.match("album/?$", request_path):
        # folders
        doc_type = "folder"
        doc_sort = albums_home_sort
        under = albums_root
    else:
        doc_type = "image"
        doc_sort = album_items_sort
        under = "%s/%s" % (albums_root, request_path.split("/", 1)[-1].strip("/"))
        folder_doc = get_record_by_path(bucket=bucket, path=under)
        if folder_doc:
            page_title = folder_doc.get("title") or get_just_name(folder_doc.get("path"), for_folder=True)
        else:
            page_title = get_just_name(under, for_folder=True)

    if doc_sort not in ["date", "-date"]:
        doc_sort = "-date"

    limit = 15 # todo 可以设定?
    doc_level = 1

    # min_images_count = 1
    docs = Data.get_data(path=under, type=doc_type,
                         limit=limit, level=doc_level, sort=doc_sort, pager_name='album_docs_pager', exclude='default')

    if doc_type == "folder":
        for doc in docs:
            doc_path = get_path_from_record(doc, is_lower=True)
            relative_path = doc_path.replace(albums_root.lower(), "", 1).strip("/")
            doc["album_url"] = "/album/%s" % relative_path

    return render_api_template("builtin_theme_album_waterfall.jade", docs=docs, page_title=page_title,)

