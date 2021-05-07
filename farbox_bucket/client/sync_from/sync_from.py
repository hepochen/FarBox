#coding: utf8
import os
import datetime
try: import send2trash
except: send2trash = None
from functools import partial
from farbox_bucket import settings
from farbox_bucket.utils import get_md5_for_file, smart_str
from farbox_bucket.utils.error import print_error
from farbox_bucket.utils.path import join, make_sure_path, read_file
from farbox_bucket.client.message import send_message


def default_get_cursor_func(root):
    if not os.path.isdir(root):
        return
    cursor_file = join(root, ".farbox.cursor")
    if os.path.isfile(cursor_file):
        return read_file(cursor_file)
    else:
        return None


def default_set_cursor_func(root, cursor):
    cursor_file = join(root, ".farbox.cursor")
    try:
        with open(cursor_file, "wb") as f:
            f.write(cursor)
            return  True
    except:
        return False


def store_sync_from_log(root, log):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = smart_str('%s %s\n\n' % (now, log))
    sync_log_filepath = join(root, '.sync/farbox_sync_from.log')
    try:
        make_sure_path(sync_log_filepath)
        with open(sync_log_filepath, 'a') as f:
            f.write(log)
    except:
        pass




def sync_from_farbox(root, private_key, node,
                     get_cursor_func=None, save_cursor_func=None,
                     before_file_sync_func=None, after_file_sync_func=None, per_page=30):
    get_cursor_func = get_cursor_func or partial(default_get_cursor_func, root)
    save_cursor_func = save_cursor_func or partial(default_set_cursor_func, root)
    cursor = get_cursor_func()

    message = dict(per_page=per_page)
    if cursor:
        message["cursor"] = cursor

    records = send_message(node, private_key, action="show_records", message=message)
    if not isinstance(records, (list, tuple)):
        if settings.DEBUG:
            print("error:records from node is not list/tuple type")
        return

    #if settings.DEBUG:
    #    print("get %s records from node" % len(records))

    last_cursor = None
    error_happened = False
    will_continue = False
    if len(records) == per_page:
        will_continue = True
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = record.get("_id")
        server_side_file_version = record.get("version")
        last_cursor = record_id
        path = record.get("path")
        if not record_id or not path:
            continue
        is_dir = record.get("is_dir")
        if is_dir:
            continue
        is_deleted = record.get("is_deleted")
        if is_deleted:
            # 为了避免误删除，忽略 is_deleted 的逻辑
            continue
        abs_filepath = join(root, path)
        if server_side_file_version and os.path.isfile(abs_filepath):
            if get_md5_for_file(abs_filepath) == server_side_file_version:
                # 文件已经存在且重复了
                #if settings.DEBUG:
                    #print("has same file on server side for %s" % abs_filepath)
                continue

        # 开始下载文件
        # 302 的跳转会自动处理，从而获得 200 的最终结果
        response = send_message(node, private_key, action="download_file",  message=dict(record_id=record_id), timeout=120, return_response=True)
        if not response:
            error_happened = True
            continue
        if response.status_code == 404: # 404 就直接忽略
            continue
        elif response.status_code not in [200, 201]:
            error_happened = True
            continue

        raw_file_content = response.content
        if not raw_file_content:
            continue

        # 存储前的 hook, 比如做版本的存储
        if before_file_sync_func and hasattr(before_file_sync_func, "__call__"):
            before_file_sync_func(abs_filepath)

        # 如果文件已经存在，保存之前，先放到回收站了，给用户多一个反悔的可能；另外 Windows 上 send2trash 并不总是正确的，except 就直接 pass
        if os.path.isfile(abs_filepath) and send2trash is not None:
            try: send2trash.send2trash(abs_filepath)
            except: pass


        try:
            make_sure_path(abs_filepath)
            with open(abs_filepath, "wb") as f:
                f.write(smart_str(raw_file_content))
            if settings.DEBUG:
                print("downloaded %s" % abs_filepath)
        except:
            if settings.DEBUG:
                print_error()
            error_happened = True

        # 存储后的 hook
        if after_file_sync_func and hasattr(after_file_sync_func, "__call__"):
            after_file_sync_func(abs_filepath)

        # 存储日志
        store_sync_from_log(root, abs_filepath)


    if not error_happened and last_cursor:
        # 没有错误发生，才会保存 cursor，确保同步的数据尽可能保持一致性
        cursor_saved = save_cursor_func(last_cursor)
        if cursor_saved and will_continue:
            # 继续调用
            sync_from_farbox(root=root, node=node, private_key=private_key,
                             get_cursor_func = get_cursor_func, save_cursor_func=save_cursor_func,
                             before_file_sync_func = before_file_sync_func, after_file_sync_func=after_file_sync_func,
                             per_page = per_page)
        else:
            if cursor_saved:
                store_sync_from_log(root, "records updated")
            else:
                store_sync_from_log(root, "sync finished, no need to update")
            if settings.DEBUG:
                print("sync-from finished, %s records" % len(records))


