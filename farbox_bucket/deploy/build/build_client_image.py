# coding: utf8
from farbox_bucket.utils import to_bytes, string_types, get_kwargs_from_console
from xserver.docker_image.utils import build_docker_image


docker_file_content = """FROM hepochen/pyweb:201908
RUN apt-get -qq update
ENV PYTHONIOENCODING=utf-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
RUN apt-get install -y locales && locale-gen en_US.UTF-8
RUN pip install farbox_bucket
CMD ["/usr/bin/python", "-m", "farbox_bucket.client.run"]
"""



# docker build -f Dockerfile -t hepochen/farbox_client:latest .

def build_farbox_client_image(image_version):
    build_docker_image(
        image_name = 'farbox_client',
        image_version = image_version,
        docker_file_content = docker_file_content,
    )


# build_farbox_client version=202105
def build_farbox_client_image_from_console():
    kwargs = get_kwargs_from_console()
    image_version = kwargs.get('version') or '202105'
    build_farbox_client_image(image_version)