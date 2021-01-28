# coding: utf8
from farbox_bucket.utils import to_bytes, string_types, get_kwargs_from_console
from xserver.docker_image.utils import build_docker_image


farbox_bucket_docker_file_content = """FROM hepochen/pyweb:201908

#RUN sudo apt-get install -y libssl1.0.0 openssl
#RUN pip install cryptography==2.3.1
RUN pip install farbox_bucket

RUN wget --no-check-certificate https://github.com/ideawu/ssdb/archive/master.zip
RUN apt-get install -q unzip && unzip master
RUN apt-get update && apt-get install make gcc g++ autoconf -y --force-yes
RUN cd /ssdb-master && make && make install
RUN rm /master.zip && rm -rf /ssdb-master

RUN apt-get install -y libjpeg-dev zlib1g-dev libwebp-dev
RUN apt-get update --fix-missing
RUN apt-get install -y graphicsmagick  python-pgmagick

RUN pip install https://github.com/hepochen/hoedown_misaka/archive/master.zip

RUN pip install farbox_bucket -U

# mkdir -p /mt/ssdb/data
# /usr/local/ssdb/ssdb-server /usr/local/ssdb/ssdb.conf
# rm /usr/local/ssdb/var/ssdb.pid
# /usr/local/ssdb/ssdb-server -d /usr/local/ssdb/ssdb.conf
# /usr/local/ssdb/ssdb-cli -h 127.0.0.1 -p 8888
"""


def build_farbox_bucket_image(image_version):
    build_docker_image(
        image_name = 'farbox_bucket',
        image_version = image_version,
        docker_file_content = farbox_bucket_docker_file_content,
    )


# build_farbox_bucket version=201908
def build_farbox_bucket_image_from_console():
    kwargs = get_kwargs_from_console()
    image_version = kwargs.get('version') or '201908'
    build_farbox_bucket_image(image_version)