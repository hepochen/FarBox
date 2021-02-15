# coding: utf8
from __future__ import absolute_import
from flask import request
from farbox_bucket.utils import smart_unicode, string_types
from farbox_bucket.utils.data import json_b64_dumps, json_dumps
from farbox_bucket.bucket.utils import set_bucket_configs, get_bucket_configs, get_bucket_in_request_context
from farbox_bucket.bucket.private_configs import update_bucket_private_configs, get_bucket_private_config
from farbox_bucket.bucket.token.utils import get_logined_bucket,  mark_bucket_login_by_private_key, mark_bucket_logout,\
    refresh_bucket_client_api_token, refresh_bucket_login_key, get_bucket_client_api_token, get_logined_admin_bucket
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.bucket.domain.register import register_bucket_domain, unregister_bucket_domain
from farbox_bucket.bucket.domain.utils import get_bucket_domains
from farbox_bucket.bucket.domain.info import get_is_system_domain
from farbox_bucket.bucket.service.bucket_service_info import get_bucket_service_info
from farbox_bucket.bucket.template_related.load_theme_from_template_folder import load_theme_from_template_folder_for_bucket
from farbox_bucket.bucket.template_related.bucket_template_web_api import set_bucket_pages_configs_by_web_api
from farbox_bucket.bucket.token.bucket_signature_and_check import get_signature_for_bucket
from farbox_bucket.bucket.utils import get_bucket_by_private_key
from farbox_bucket.themes import themes as builtin_themes
from farbox_bucket.settings import NODE


class Bucket(object):
    @cached_property
    def logined_bucket(self):
        # 已登录的 bucket name
        bucket_name = get_logined_bucket(check=True) or ''
        return bucket_name

    @cached_property
    def is_system_admin(self):
        return bool(get_logined_admin_bucket())

    @cached_property
    def domains(self):
        return get_bucket_domains(self.logined_bucket)

    @cached_property
    def service_info(self):
        return get_bucket_service_info(self.logined_bucket)


    @cache_result
    def toggle_enable_web_robots(self):
        update_bucket_private_configs(self.logined_bucket, enable_web_robots= (not self.enable_web_robots))
        return ""

    @cached_property
    def enable_web_robots(self):
        return get_bucket_private_config(self.logined_bucket, "enable_web_robots", default=True)

    @cache_result
    def toggle_enable_https_force_redirect(self):
        update_bucket_private_configs(self.logined_bucket, enable_https_force_redirect=(not self.enable_https_force_redirect))
        return ""

    @cached_property
    def enable_https_force_redirect(self):
        return get_bucket_private_config(self.logined_bucket, "enable_https_force_redirect", default=False)

    def is_system_domain(self, domain):
        return get_is_system_domain(domain)

    @cached_property
    def client_api_token(self):
        # 给 API 用的 Token, 需要当前 bucket 处于登录的状态
        return get_bucket_client_api_token(self.logined_bucket)

    @cached_property
    def refreshed_client_api_token(self):
        return refresh_bucket_client_api_token(self.logined_bucket)

    @cached_property
    def node(self):
        node_value = NODE or request.url_root
        return node_value

    def login(self):
        private_key = request.values.get('private_key')
        mark_bucket_login_by_private_key(private_key)
        return ''

    def logout(self):
        mark_bucket_logout()
        return ""

    def logout_all_devices(self):
        refresh_bucket_login_key(self.logined_bucket)
        return ""

    @cache_result
    def get_bucket_by_private_key(self, private_key):
        try:
            bucket_name = get_bucket_by_private_key(private_key) or 'invalid_private_key'
        except:
            bucket_name = 'invalid_private_key'
        return bucket_name

    @cache_result
    def base64_private_key(self, private_key, **kwargs):
        data = kwargs
        data['private_key'] = private_key
        return json_b64_dumps(data)

    @cached_property
    def current_bucket(self):
        return get_bucket_in_request_context() or ""


    @cache_result
    def register_domain(self, domain, admin_domain_password=None):
        if not self.logined_bucket:
            return "not-login"
        error_info = register_bucket_domain(domain=domain, bucket=self.logined_bucket, admin_password=admin_domain_password)
        if error_info:
            return error_info
        return ""


    @cache_result
    def unregister_domain(self, domain):
        if not self.logined_bucket:
            return "not-login"
        error_info = unregister_bucket_domain(domain=domain, bucket=self.logined_bucket)
        if error_info:
            return error_info
        return ""

    ###### theme related starts
    @cache_result
    def apply_builtin_theme(self, theme_key, return_result=False):
        theme_key = theme_key.lower().strip() # key 都是小写的
        theme_content = builtin_themes.get(theme_key) or ""
        if not self.logined_bucket:
            if return_result:
                return "not-login"
        if not theme_content or not isinstance(theme_content, dict):
            if return_result:
                return "not-found"
        else:
            if '_theme_key' not in theme_content:
                theme_content['_theme_key'] = theme_key
            set_bucket_configs(self.logined_bucket, theme_content, config_type='pages')
            if return_result:
                return "ok"
        return ""

    @cached_property
    def builtin_theme_keys(self):
        return builtin_themes.keys()

    @cached_property
    def page_configs(self):
        return self.get_configs(config_type="pages")

    @cached_property
    def current_theme_key(self):
        return self.page_configs.get("_theme_key") or ""


    @cached_property
    def theme_api_url(self):
        if not self.logined_bucket:
            return ""
        else:
            sign = get_signature_for_bucket(self.logined_bucket)
            url_path = "__theme?bucket=%s&sign=%s" % (self.logined_bucket, sign)
            api_url = request.url_root.rstrip("/") + "/" + url_path
            return api_url


    @cache_result
    def apply_theme(self, source):
        if not source:
            return "" # ignore
        if not self.logined_bucket:
            return "need login"
        if not isinstance(source, string_types):
            return "source type error"
        if "://" not in source and source.count("/") <= 1:
            load_theme_from_template_folder_for_bucket(self.logined_bucket, source)
            return "success to load theme from folder"
        elif "?" in source:
            if "://" not in source:
                source = "http://" + source
            done = set_bucket_pages_configs_by_web_api(self.logined_bucket, source, timeout=3)
            if not done:
                return "failed to set theme by remote url"
            else:
                return "success to set theme by remote url"
        else:
            return "source format error"

    ###### theme related ends

    @cache_result
    def get_configs(self, config_type="pages"):
        bucket = self.logined_bucket
        if not bucket:
            return {}
        else:
            return get_bucket_configs(self.logined_bucket, config_type)


@cache_result
def bucket():
    return Bucket()

