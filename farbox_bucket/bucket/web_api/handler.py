#coding: utf8
import time
from flask import request, abort
from farbox_bucket.settings import DEBUG, WEBSOCKET, MAX_FILE_SIZE
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.utils import force_to_json, string_types, to_int
from farbox_bucket.utils.web_utils.response import json_with_status_code

from farbox_bucket.bucket.utils import set_bucket_configs, has_bucket
from farbox_bucket.bucket.domain.register import register_bucket_domain, unregister_bucket_domain

from farbox_bucket.bucket.record.create import create_record
from farbox_bucket.bucket.record.get.path_related import get_record_id_by_path, get_record_by_path

from farbox_bucket.bucket.web_api.verify import get_verified_message_from_web_request
from farbox_bucket.bucket.utils import get_bucket_configs
from farbox_bucket.bucket.helper.files_related import auto_update_bucket_and_get_files_info

from farbox_bucket.server.utils.request import get_file_content_in_request

from farbox_bucket.server.realtime.utils import push_message_to_bucket
from farbox_bucket.server.statistics.post_visits import load_all_posts_visits_from_csv
from farbox_bucket.server.helpers.bucket import sync_download_file_by_web_request, show_bucket_records_for_web_request
from farbox_bucket.server.utils.response import jsonify

from farbox_bucket.themes import themes



# request 过来的必要字段 farbox_bucket.client.message: send_message & get_data_to_post
# bucket: 针对某个 bucket 的操作
# action: 当前 API 的动作
# timestamp: 与服务器上的时间差，不能超过 120s，另外也是作为内容校验的一个字段
# data: 必然是字符串，可以是 JSON，有些场合会转为 Python 的数据进行处理
# public_key: 只有 create_bucket 的时候，才会有；如果它存在，也会参与 signature 的校验


class FarBoxBucketMessageAPIHandler(object):
    def __init__(self):
        self.action_handlers = {
            'register_domain': self.register_domain,
            'unregister_domain': self.unregister_domain,
            'should_upload_file': self.should_upload_file,
            'upload_file': self.upload_file,
            'show_files': self.show_files,

            # download_file + show_records 可以实现反向同步到 client 的逻辑
            "download_file": self.download_file,
            "show_records": self.show_records,

            'check': self.check_bucket,
            'set_bucket_theme': self.set_bucket_theme,
            'check_filepaths': self.check_filepaths,
            'get_configs': self.get_configs,

            # 如上没有匹配，就是 create_record 了
        }

    def get_verified_message(self):
        # not dict, means error info
        verified_message = get_verified_message_from_web_request()
        # verified_message = dict(
        #         bucket = bucket,
        #         action = action,
        #         data = data, # string
        #         public_key = public_key,
        #     )
        return verified_message

    @property
    def verified_message(self): # auto cached in current request
        if hasattr(request, 'bucket_verified_message'):
            return request.bucket_verified_message
        else:
            verified_message = self.get_verified_message()
            request.bucket_verified_message = verified_message
            return verified_message

    @property
    def public_key(self):
        # 不从 request 中获得，除了 create_bucket 需要传入 public_key 之外， 其它时候从数据库中获得就可以了
        return self.verified_message.get('public_key')

    @property
    def bucket(self):
        return request.values.get('bucket')

    @property
    def action(self):
        return request.values.get('action')

    @property
    def raw_data(self):
        return self.verified_message.get('data')

    @property
    def raw_json_data(self): # must be a dict
        j_data = force_to_json(self.raw_data)
        if not isinstance(j_data, dict):
            j_data = {}
        return j_data

    def get_value_from_data(self, key):
        # message 有固定的数据格式，更多的是在 raw_data 中的 json_data 逻辑中
        json_data = self.raw_json_data
        return json_data.get(key)

    def get_values_from_data(self, *keys):
        # 多个 keys，返回对应的 value-list
        json_data = self.raw_json_data
        values = []
        for key in keys:
            values.append(json_data.get(key))
        return values


    def handle(self):
        if not isinstance(self.verified_message, dict):  # 校验出错了
            return json_with_status_code(500, message=self.verified_message)

        action = request.values.get('action') or ''
        action_handler = self.action_handlers.get(action)
        if not action_handler and action.startswith('config_'):
            action_handler = self.update_bucket_config
        if not action_handler:
            action_handler = self.create_record

        # call the action_handler, should return a response
        return action_handler()


    def do(self):
        return self.handle()

    def return_response(self):
        return self.handle()

    ########### actions below ##############


    def register_domain(self):
        domain = self.get_value_from_data('domain')
        admin_password = self.get_value_from_data('admin_password')
        if not domain:
            return json_with_status_code(400, 'no domain in your request')
        else:
            error_info = register_bucket_domain(domain=domain, bucket=self.bucket, admin_password=admin_password)
            if error_info:
                return json_with_status_code(400, error_info)
            else:
                return json_with_status_code(200, 'ok')


    def unregister_domain(self):
        domain = self.get_value_from_data('domain')
        if not domain:
            return json_with_status_code(400, 'no domain in your request')
        else:
            error_info = unregister_bucket_domain(domain=domain, bucket=self.bucket)
            if error_info:
                return json_with_status_code(400, error_info)
            else:
                return json_with_status_code(200, 'ok')


    def update_bucket_config(self):
        config_type = self.action.replace('config_', '').strip()
        configs = self.raw_json_data
        updated = set_bucket_configs(self.bucket, configs, config_type=config_type)
        if config_type in ['files', 'file']:
            # 不由 client 端设定 files 的信息
            return json_with_status_code(200, 'ok')
        if WEBSOCKET and config_type == 'pages' and configs.get('__changed_filepaths'):
            # 推送 websocket 的通知, 如果启用了 websocket 的话，这样可以实时刷新 template
            changed_filepaths = configs.get('__changed_filepaths')
            message_to_push = dict(changed_filepaths=changed_filepaths, date=time.time())
            push_message_to_bucket(bucket=self.bucket, message=message_to_push)
        if not updated:
            return json_with_status_code(400, 'configs format error or no bucket matched')
        else:
            # 先移除 ipfs 相关的逻辑 @2021-2-4
            # from farbox_bucket.ipfs.server.ipfs_bucket import mark_bucket_to_sync_ipfs
            #if config_type == 'files':
                # todo 这里处理是否妥当？？
                #mark_bucket_to_sync_ipfs(self.bucket)
            return json_with_status_code(200, 'ok')


    def set_bucket_theme(self):
        # 从系统默认提供的 theme 中进行直接的设定
        theme_key = self.raw_json_data.get('theme') or self.raw_json_data.get('theme_key')
        theme_content = themes.get(theme_key) or ''
        if not theme_content or not isinstance(theme_content, dict):
            return json_with_status_code(404, 'can not find the theme')
        else:
            if '_theme_key' not in theme_content:
                theme_content['_theme_key'] = theme_key
            set_bucket_configs(self.bucket, theme_content, config_type='pages')
            return json_with_status_code(200, 'ok')


    def create_record(self):
        # the default action
        version = self.raw_json_data.get("version")
        path = self.raw_json_data.get("path")
        if path and path.endswith(".md"):
            pass
        if version and path:
            old_record = get_record_by_path(bucket=self.bucket, path=path)
            if old_record and old_record.get("version") == version:
                if DEBUG:
                    print("same file for %s" % path)
                return json_with_status_code(200, 'ok')
        elif path and self.raw_json_data.get("is_dir") and not self.raw_json_data.get("is_deleted", False):
            # folder 不需要重新处理
            old_record = get_record_by_path(bucket=self.bucket, path=path)
            if old_record:
                return json_with_status_code(200, 'ok')

        error_info = create_record(self.bucket, self.raw_data)
        if error_info:
            return json_with_status_code(400, error_info)
        else:
            # record 已经创建成功了：
            # 1. visits & comments 这些动态的数据要到数据库里
            # 2. 把 private_key_md5 进行存储，可以对一些数据进行加密、解密
            json_data = self.raw_json_data
            if isinstance(json_data, dict):
                record_type = json_data.get('_type')
                path = json_data.get('path')
                if not isinstance(path, string_types):
                    path = ''
                path = path.strip('/').lower()
                if record_type == 'visits' and path == '_data/visits.csv':
                    load_all_posts_visits_from_csv(self.bucket, json_data)

            return json_with_status_code(200, 'ok')



    def should_upload_file(self):
        file_size = self.raw_json_data.get("size") or self.raw_json_data.get("file_size")
        if file_size > MAX_FILE_SIZE:
            should = False
        else:
            should = storage.should_upload_file_by_client(self.bucket, self.raw_json_data)
        return json_with_status_code(200, 'yes' if should else 'no')


    def upload_file(self):
        path = self.raw_json_data.get('path')
        if not path:
            return json_with_status_code(400, 'path required')

        accepted = False
        info = storage.accept_upload_file_from_client(self.bucket, self.raw_json_data,
                                                      get_raw_content_func=get_file_content_in_request)
        if info == 'ok':
            accepted = True

        if accepted:
            # 没有路径对应的 record，直接进行上传的行为, 创建一个 record
            record_id = get_record_id_by_path(self.bucket, path)
            if not record_id:
                create_record(self.bucket, record_data=self.raw_json_data)
            return json_with_status_code(200, 'ok')
        else:
            return json_with_status_code(400, info)

    def show_files(self):
        files = auto_update_bucket_and_get_files_info(self.bucket)
        return json_with_status_code(200, files)


    def download_file(self):
        record_id = self.raw_json_data.get("record") or self.raw_json_data.get("record_id")
        if not record_id:
            abort(404, "no record_id")
        elif not self.bucket:
            abort(404, "no bucket matched")
        else:
            return sync_download_file_by_web_request(bucket=self.bucket, record_id=record_id)

    def show_records(self):
        if not self.bucket:
            return jsonify([])
        else:
            per_page = to_int(self.raw_json_data.get("per_page")) or 10
            response = show_bucket_records_for_web_request(self.bucket,
                                                       cursor=self.raw_json_data.get("cursor"),
                                                       per_page=per_page, includes_zero_ids=False)
            return response


    def check_bucket(self):
        if self.bucket and has_bucket(self.bucket):
            return json_with_status_code(200, 'ok')
        else:
            return json_with_status_code(404, 'not found')


    def check_filepaths(self):
        filepaths = self.raw_json_data.get('filepaths') or self.raw_json_data.get('paths')
        if not isinstance(filepaths, (list, tuple)):
            filepaths = []
        result = {}
        for path in filepaths:
            path_record_id = get_record_id_by_path(self.bucket, path) or ''
            result[path] = path_record_id
        return json_with_status_code(200, result)


    def get_configs(self):
        config_type = self.raw_json_data.get('type') or self.raw_json_data.get('config_type') or 'site'
        if config_type == "files":
            configs = auto_update_bucket_and_get_files_info(self.bucket)
        else:
            configs = get_bucket_configs(self.bucket, config_type=config_type)
        return json_with_status_code(200, configs)
