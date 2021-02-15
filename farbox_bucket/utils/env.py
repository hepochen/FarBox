#coding: utf8
from __future__ import absolute_import
import os
import json
from farbox_bucket.utils.path import read_file, make_sure_path, write_file


def _get_env(key):
    lower_key = key.lower()
    upper_key = key.upper()
    v = os.environ.get(key) or os.environ.get(lower_key) or os.environ.get(upper_key)
    if v:
        return v
    filenames  = [key, '%s.json'%key, '%s.txt'%key]
    if lower_key not in filenames:
        filenames += [lower_key, '%s.txt'%lower_key]
    for filename in filenames:
        filepath1 = os.path.join('/tmp/env', filename)
        filepath2 = os.path.join('/env', filename)
        filepath3 = os.path.join('/mt/web/configs', filename)
        filepaths = [filepath1, filepath2, filepath3]
        path_in_env = os.environ.get(key + '_filepath')
        if path_in_env:
            filepaths.append(path_in_env)
        for filepath in filepaths:
            if os.path.isfile(filepath) and os.path.getsize(filepath) < 10*1024:
                try:
                    with open(filepath, 'rb') as f:
                        raw_content = f.read()
                except:
                    continue
                v = raw_content.strip()
                if v:
                    # cache it
                    os.environ[key] = v
                    return v


app_global_envs_may_be_paths = ["/mt/web/data/configs.json",
                                "/mt/web/configs/configs.json",
                                "/tmp/farbox_bucket_configs.json"]


app_global_config_folder = "/mt/web/configs"
app_nginx_server_ssl_cert_filepath = "/mt/web/configs/nginx/server.crt"
app_nginx_server_ssl_key_filepath = "/mt/web/configs/nginx/server.key"



def store_nginx_server_cert(ssl_key, ssl_cert):
    if not ssl_key or not ssl_cert:
        return
    old_ssl_key = read_file(app_nginx_server_ssl_key_filepath)
    old_ssl_cert = read_file(app_nginx_server_ssl_cert_filepath)
    if old_ssl_key != ssl_key or old_ssl_cert != ssl_cert:
        make_sure_path(app_nginx_server_ssl_cert_filepath, is_file=True)
        write_file(app_nginx_server_ssl_key_filepath, ssl_key)
        write_file(app_nginx_server_ssl_cert_filepath, ssl_cert)
        # reload nginx
        c_f = os.popen("/usr/nginx/sbin/nginx -s reload")
        try: c_f.read()
        except: pass



def set_app_global_envs(envs_configs):
    # /mt/web/data 的优先，这样 container 的变化， /mt/web/configs 的变化也不会影响到
    if not isinstance(envs_configs, dict):
        return
    try:
        content_to_write = json.dumps(envs_configs)
        for path in app_global_envs_may_be_paths:
            try:
                with open(path, "wb") as f:
                    f.write(content_to_write)
                # 保存主域名的 SSL 证书，主要是提供给二级域名的 wilde ssl
                store_nginx_server_cert(envs_configs.get("domain_ssl_key"), envs_configs.get("domain_ssl_cert"))
                return
            except:
                pass
    except:
        return


def load_app_global_envs():
    for path in app_global_envs_may_be_paths:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    raw_content = f.read()
                data = json.loads(raw_content)
                if isinstance(data, dict):
                    return data
            except:
                pass
    return {} # by default


global_envs = None
def get_global_envs():
    global global_envs
    if global_envs is None:
        global_envs = load_app_global_envs()
    return global_envs



def get_env(key):
    envs = get_global_envs()
    lower_key = key.lower()
    if lower_key in envs:
        matched_value = envs.get(lower_key)
        if matched_value is not None and matched_value != "":
            return matched_value
    return _get_env(key)

