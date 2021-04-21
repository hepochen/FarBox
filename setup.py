#/usr/bin/env python
# coding: utf8
import re
from setuptools import setup, find_packages
from farbox_bucket import version

raw_pipfile_packages = """
pyssdb = "==0.4.1"
ujson = "==2.0.3"
pyopenssl = "==18.0.0"
flask = "==0.10"
psutil = "*"
jinja2 = "==2.9"
pycrypto = "==2.6.1"
python-dateutil = "*"
shortuuid = "==0.5.0"
pymemcache = "==2.1.1"
pyjade = "==2.0.3"
raven = "*"
blinker = "==1.4"
gevent = "==1.4.0"
dnspython = "==1.16.0"
farbox-markdown = "*"
farbox-misaka = "*"
unidecode = "==1.1.1"
pyscss = "==1.3.5"
cryptography = "==2.3.1"
xserver = "*"
pillow = "==5.4.1"
cos-python-sdk-v5 = "==1.9.0"
itsdangerous = "==1.1.0"
boto3 = "==1.17.54"
farbox-gevent-websocket = "*"
elasticsearch = "==7.10.1"
xmltodict = "==0.12.0"
Send2Trash = "==1.5.0"
"""
# boto = "==2.38.0"

pipfile_packages = []
for pip_package_name, pip_package_version in re.findall('([\w-]+)\s*=\s*.*?(?:==)?([0-9.*]+)', raw_pipfile_packages):
    if pip_package_version in ['*']:
        pipfile_packages.append(pip_package_name)
    elif pip_package_version in ['.']:
        continue
    else:
        if pip_package_name in ['pillow']:
            pipfile_packages.append('%s>=%s' % (pip_package_name, pip_package_version))
        else:
            pipfile_packages.append('%s==%s'%(pip_package_name, pip_package_version))


setup(
    name='farbox_bucket',
    version=version,
    description='FarBox Bucket',
    author='Hepochen',
    author_email='hepochen@gmail.com',
    include_package_data=True,
    packages=find_packages(),

    install_requires = pipfile_packages + [
        # for cryptography starts
        'setuptools>=40.0.0',
        'enum34',
        # for cryptography ends
    ],

    entry_points={
        'console_scripts':[
            'farbox_bucket = farbox_bucket.console:main',
            'build_farbox_bucket = farbox_bucket.deploy.build.build_image:build_farbox_bucket_image_from_console',

            'update_deploy_farbox_bucket = farbox_bucket.deploy.deploy:update_deploy_farbox_bucket',
            'deploy_farbox_bucket = farbox_bucket.deploy.deploy:deploy_from_console',

            'farbox_bucket_upgrade = farbox_bucket.deploy.deploy:upgrade_farbox_bucket',
            'farbox_bucket_update_web = farbox_bucket.deploy.deploy:update_farbox_bucket_web',
            'farbox_bucket_restart_web = farbox_bucket.deploy.deploy:update_farbox_bucket_web',
            'farbox_bucket_restart_cache = farbox_bucket.deploy.deploy:restart_farbox_bucket_cache',
        ]
    },

    platforms = 'linux',
)