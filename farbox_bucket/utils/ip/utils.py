# coding: utf8
from __future__ import absolute_import
import socket, binascii, os, re, requests


def ip_to_integer(ip_address):
    version = socket.AF_INET
    try:
        ip_hex = socket.inet_pton(version, ip_address)
        ip_integer = int(binascii.hexlify(ip_hex), 16)
        return ip_integer
    except:
        pass
    raise ValueError("invalid IP address")


def subnetwork_to_ip_range(subnetwork):
    try:
        fragments = subnetwork.split('/')
        network_prefix = fragments[0]
        netmask_len = int(fragments[1])
        ip_len = 32
        try:
            suffix_mask = (1 << (ip_len - netmask_len)) - 1
            netmask = ((1 << ip_len) - 1) - suffix_mask
            ip_hex = socket.inet_pton(socket.AF_INET, network_prefix)
            ip_lower = int(binascii.hexlify(ip_hex), 16) & netmask
            ip_upper = ip_lower + suffix_mask
            return ip_lower, ip_upper
        except:
            pass
    except:
        pass

    raise ValueError("invalid subnetwork")


def load_ip_subsets(filepath):
    if not filepath or not os.path.isfile(filepath):
        return []
    with open(filepath) as f:
        raw_content = f.read()
    lines = raw_content.split('\n')
    subsets = []
    for line in lines:
        line = line.strip()
        try:
            subset = subnetwork_to_ip_range(line)
            subsets.append(subset)
        except:
            pass
    subsets.sort()
    return subsets


def search_ip_in_subsets(subsets, ip):
    try:
        ip = ip_to_integer(ip)
    except:
        return
    low = 0
    height = len(subsets)-1
    tried = 0
    while low < height:
        tried += 1
        mid = (low+height)/2
        mid_obj = subsets[mid]
        start, end = mid_obj
        if end >= ip >= start:
            #print tried
            return mid_obj
        elif ip > end:
            low = mid + 1
        else: # ip < start
            height = mid - 1
    #print tried
    return None

#subsets = load_ip_subsets('/Users/hepochen/Dev/QuanDuan/LazyHosts/resources/china_ip_list.txt')
#print search_ip_in_subsets(subsets, '223.202.224.10')

def is_ipv4_ip(ip):
    if isinstance(ip, (str,unicode)):
        ip = ip.strip()
        if len(ip) > 100:
            return False
        if re.match('\d+\.\d+\.\d+\.\d+$', ip):
            ip_parts = ip.split('.')
            if ip_parts[0] == '0':
                return False
            for value in ip_parts:
                value = int(value)
                if value < 0 or value > 255:
                    return False
            return True
    return False


def get_current_ip():
    ip_in_env = os.environ.get('HOSTIP')
    if ip_in_env:
        return ip_in_env
    # hostname 本身就是 ip 地址的
    hostname = socket.gethostname()
    if is_ipv4_ip(hostname):
        return hostname
    try:
        try:
            with open('/tmp/ip.txt') as f:
                return f.read().strip()
        except:
            pass
        ip = requests.get('http://api.ipify.org').text
        try:
            with open('/tmp/ip.txt', 'w') as f:
                f.write(ip)
        except:
            pass
        return ip
    except:
        return ''