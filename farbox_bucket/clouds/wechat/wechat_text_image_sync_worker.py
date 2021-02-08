#coding: utf8
import re
from farbox_bucket.utils import smart_unicode
from farbox_bucket.bucket.utils import get_now_from_bucket
from farbox_bucket.bucket.record.get.path_related import get_json_content_by_path
from farbox_bucket.server.helpers.file_manager_downloader import download_from_internet_and_sync
from farbox_bucket.server.helpers.markdown_doc_append_worker import append_to_markdown_doc_and_sync
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side

from .bind_wechat import set_name_by_wechat_user_id, get_name_by_wechat_user_id


#    #tag #hello [[ #wiki_tag ]] [[#more]] test
def compile_tag_to_wiki_link_syntax(content, is_voice=False):
    content = re.sub("(?<!\[)(#[^# \t]+)", "[[\g<1>]]", content)
    content = re.sub("(\[\s*){2,}\[", "[[", content)
    content = re.sub("(\]\s*){2,}\]", "]]", content)
    if is_voice and u"标签" in content:
        p1, p2 = content.rsplit(u"标签", 1)
        if u"，" not in p2:
            p2 = p2.replace(u"。", "").strip()
            if len(p2) <= 5:
                content = u"%s[[#%s]]。" % (p1, p2)
    return content


def wechat_text_image_handler(wechat_user_id, bucket, xml_data):
    msg_id = xml_data.get("MsgId")
    create_time = xml_data.get("CreateTime")
    msg_type = xml_data.get("MsgType")

    # post_root, auto_add_date(bool), silent_reply(bool), image_folder, image_insert_type(image/markdown_syntax)
    wechat_configs = get_json_content_by_path(bucket, "__wechat.json", force_dict=True)

    today = get_now_from_bucket(bucket, "%Y-%m-%d")
    silent_reply = wechat_configs.get("silent_reply") or False
    post_root = (wechat_configs.get("post_folder") or "").strip("/")
    auto_add_date = wechat_configs.get("auto_add_date", False)
    add_nickname = wechat_configs.get("add_nickname", False)
    draft_by_default = wechat_configs.get("draft_by_default", False)
    one_user_one_post = wechat_configs.get("one_user_one_post", False)

    if msg_type == "image":  # 纯图片
        pic_url = xml_data.get("PicUrl")
        if not pic_url:
            return "error: PicUrl is blank"
        filename = "%s.jpg" % (msg_id or create_time)
        image_insert_type = wechat_configs.get("image_insert_type")
        raw_image_folder = smart_unicode(wechat_configs.get("image_folder") or "").strip("/")
        image_folder = smart_unicode(raw_image_folder) or today
        if image_insert_type == "image":  # 直接保存图片
            path = "%s/%s" % (image_folder, filename)
            download_from_internet_and_sync(bucket=bucket, url=pic_url, path=path, timeout=60) # 下载图片并进行保存
            if silent_reply:
                return ""
            else:
                return u"将保存到 %s" % path
        else:
            if raw_image_folder:
                # 还是按照 day 增加一层子目录，避免多了找不到的情况
                path = "/%s/%s/%s" % (raw_image_folder, today, filename)
            else:
                path = "/_image/%s/%s" % (today, filename)
            text_to_append = "![](%s)" % path  # 插入图片的语法
            download_from_internet_and_sync(bucket=bucket, url=pic_url, path=path, timeout=60)
    else:
        text_to_append = xml_data.get("Content") or xml_data.get("Recognition") or xml_data.get("EventKey") or ""

    text_to_append = text_to_append.strip()

    if "\n" not in text_to_append and re.match(u"name ", text_to_append):
        name = text_to_append[5:].strip()
        if name:
            set_name_by_wechat_user_id(wechat_user_id, name)
            return u"昵称已设定为 %s" % name

    if one_user_one_post:
        if post_root:
            post_path = "%s/%s.txt" %  (post_root, wechat_user_id)
        else:
            post_path = "%s.txt" % wechat_user_id
    else:
        if post_root:
            post_path = post_root + "/" + get_now_from_bucket(bucket, "%Y-%m-%d.txt")
        else:
            post_path = get_now_from_bucket(bucket, "%Y/%Y-%m-%d.txt")


    if text_to_append.strip() == "reset":
        if one_user_one_post:
            sync_file_by_server_side(bucket=bucket, relative_path=post_path, content=" ")
            return u"%s 已重置" % post_path
        else:
            return u"只有 `One User One Post` 的时候才能使用 reset 命令。"

    if text_to_append:
        if add_nickname:
            nickname = get_name_by_wechat_user_id(wechat_user_id)
            if nickname:
                text_to_append = "%s: %s" % (nickname, text_to_append)

        if auto_add_date and "\n" not in text_to_append:
            if text_to_append.startswith("---") or re.match(u"\w+[:\uff1a]", text_to_append):
                auto_add_date = False
        if auto_add_date: # 添加时间戳
            bucket_now = get_now_from_bucket(bucket, "%Y-%m-%d %H:%M:%S")
            text_to_append = "%s %s"%(bucket_now, text_to_append)

        is_voice = True if xml_data.get("Recognition") else False
        text_to_append = compile_tag_to_wiki_link_syntax(text_to_append, is_voice=is_voice)

        # 保存文章, 5 分钟的间隔自动多一个空line
        append_to_markdown_doc_and_sync(bucket=bucket, path=post_path, content=text_to_append,
                                        lines_more_diff=5*60, draft_by_default=draft_by_default)

        if silent_reply:
            return ""
        else:
            return u"已保存至 %s" % post_path
