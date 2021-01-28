# coding: utf8
import os

docker_ips_filepath = '/mt/docker/log/ips.txt'

# 在一个docker 容器启动的时候，总是 -v /log/docker:/mt/docker/log
# 而主机中，总是在启动容器的时候 获得 ips.txt 的对应，从而可以在一个container内，获得所有容器能对应的ip

def get_docker_ips(filepath):
    ip_map = {}
    if not os.path.isfile(filepath):
        return ip_map
    with open(filepath) as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line:
                line_parts = line.split(' ')
                if len(line_parts) == 2:
                    docker_container, ip = line_parts
                    docker_container = docker_container.strip().strip('/')
                    ip_map[docker_container] = ip
    return ip_map


def get_docker_ip(container_names):
    if not isinstance(container_names, (list, tuple)):
        container_names = [container_names]
    ip_map = get_docker_ips(docker_ips_filepath)
    for container_name in container_names:
        ip = ip_map.get(container_name)
        if ip:
            return ip
    return ''



