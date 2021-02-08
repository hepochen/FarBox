# coding: utf8
import os
import re
from farbox_bucket.utils.env import get_global_envs
from farbox_bucket.utils.memcache import cache_client


# /usr/local/bin/supervisorctl

def auto_reset_elasticsearch_memory_config_when_app_started():
    block_key = "elasticsearch_memory_config_block_key"
    if cache_client.get(block_key):
        # 避免多个 instance 起来的时候，反复重启 elasticsearch 的情况
        return
    else:
        cache_client.set(block_key, "yes", expiration=60)
    system_configs = get_global_envs()
    reset_elasticsearch_memory_config(system_configs, es_mem_config_filepath = "/elasticsearch/config/jvm.options")



def reset_elasticsearch_memory_config(system_configs, es_mem_config_filepath = "/elasticsearch/config/jvm.options"):
    if not os.path.isfile(es_mem_config_filepath):
        return
    elasticsearch_memory = system_configs.get("elasticsearch_memory")
    if not elasticsearch_memory:
        return
    try:
        elasticsearch_memory = elasticsearch_memory.strip()
        if not re.match("\d+[mg]$", elasticsearch_memory, flags=re.I):
            return
    except:
        return
    with open(es_mem_config_filepath, "rb") as f:
        old_es_mem_config = f.read()

    new_es_mem_config =  old_es_mem_config
    new_es_mem_config = re.sub("\n-Xms\d+[gm]", "\n-Xms%s"%elasticsearch_memory, new_es_mem_config)
    new_es_mem_config = re.sub("\n-Xmx\d+[gm]", "\n-Xmx%s" % elasticsearch_memory, new_es_mem_config)
    if new_es_mem_config != old_es_mem_config:
        print("will update elasticsearch memory")
        try:
            with open(es_mem_config_filepath, "wb") as f:
                f.write(new_es_mem_config)
        except:
            pass
        try:
            with os.popen("/usr/local/bin/supervisorctl restart elasticsearch") as c_f:
                c_f.read()
        except:
            pass
    else:
        print("no need to update elasticsearch memory")
