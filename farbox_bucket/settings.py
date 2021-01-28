#coding: utf8
from __future__ import absolute_import
import re, os, sys, uuid
from raven import Client
from farbox_bucket.utils import to_float
from farbox_bucket.utils.path import read_file, write_file
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.ssdb_client import SSDB_Client
from farbox_bucket import version
from farbox_bucket.utils.encrypt.simple import ServerSerializer

ssdb_ip = get_env('SSDB_IP')  or '127.0.0.1'
ssdb_port = get_env('SSDB_PORT') or 8888
try:
    ssdb_port = int(ssdb_port)
except:
    ssdb_port = 8888


db_client = SSDB_Client(ssdb_ip, ssdb_port)


STATIC_FILE_VERSION = version # 静态资源通过 h.load 载入的时候，增加 version 的逻辑

MAX_RECORD_SIZE = 300 * 1024 # 300Kb

MAX_RECORD_SIZE_FOR_CONFIG = 800 * 1024 ## 800Kb



# 如果是负数，则没有邀请的权限，0 则是处于 open 的状态; ADMIN_BUCKET 始终有邀请的权限。
# 如果是整数，则表示一个 bucket 创建多少天后，才能邀请别人的 bucket
# 默认值是 -1，也就是必须邀请，才能创建 bucket
try:
    ALLOWED_INVITE_DAYS = float((get_env('ALLOWED_INVITE_DAYS') or '').strip())
except:
    ALLOWED_INVITE_DAYS = -1


ADMIN_BUCKET = get_env('ADMIN_BUCKET') or ''


DEBUG = bool(get_env('DEBUG'))

WEBSOCKET = bool(get_env('WEBSOCKET'))



# 允许服务的提供者，直接使用 py 脚本进行处理
bucket_scripts_root = '/mt/web/configs/bucket_scripts'
if DEBUG:
    bucket_scripts_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test_bucket_scripts')
if os.path.isdir(bucket_scripts_root):
    sys.path.append(bucket_scripts_root)


BUCKET_PRICE = to_float(get_env("bucket_price"), default_if_fail=99) or 0
BUCKET_PRICE2 = to_float(get_env("bucket_price2"), default_if_fail=0) or 0


def get_domains_from_env(key):
    raw_domains = get_env(key) or ''
    domain_list = re.split('[,\n]', raw_domains)
    domains_got = []
    for domain in domain_list:
        domain = domain.strip().lower()
        if domain not in domains_got and domain:
            domains_got.append(domain)
    return domains_got


SYSTEM_DOMAINS = get_domains_from_env('DOMAINS')


# 注册系统级的 domain 时候会需要用到
try:
    ADMIN_DOMAIN_PASSWORD = get_env('ADMIN_DOMAIN_PASSWORD').strip()
except:
    ADMIN_DOMAIN_PASSWORD = ''

WEBSITE_DOMAINS = []
for domain in SYSTEM_DOMAINS+get_domains_from_env('SITE_DOMAINS'):
    www_domain = 'www.%s'%domain
    WEBSITE_DOMAINS += [domain, www_domain]

# node is a domain
NODE = get_env('NODE') or ''
if not NODE and SYSTEM_DOMAINS:
    NODE = SYSTEM_DOMAINS[0]


sentry_dsn = get_env('SENTRY')
if sentry_dsn:
    sentry_client = Client(sentry_dsn)
else:
    sentry_client = None


server_secret_key = get_env('SERVER_SECRET_KEY')
if not server_secret_key:
    server_secret_key_filepath = "/tmp/farbox_server_secret_key"
    server_secret_key = read_file(server_secret_key_filepath)
    if not server_secret_key:
        server_secret_key =  uuid.uuid1().hex
        try: write_file(server_secret_key_filepath, server_secret_key)
        except: pass

signer = ServerSerializer(server_secret_key)


# aws ses mail sender
SES_ID = get_env('SES_ID')
SES_KEY = get_env('SES_KEY')
SES_SENDER = get_env('SES_SENDER') or 'No-Reply<no-reply@domain.com>'

CAN_SEND_SYSTEM_EMAIL = bool(SES_ID and SES_KEY)


# todo 这里应该允许二次定制的时候，进行自定义的逻辑
BASIC_FORM_FORMATS = {}

# todo DEFAULT_SERVER_NODE ?