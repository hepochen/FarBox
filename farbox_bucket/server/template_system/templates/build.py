# coding: utf8
import os
import json
from farbox_bucket.utils import smart_unicode
from farbox_bucket.utils.path import write_file
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html


def get_templates_info():
    templates_info = {}
    templates_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    if not os.path.isdir(templates_folder):
        return templates_info
    filenames = os.listdir(templates_folder)
    for filename in filenames:
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        filepath = os.path.join(templates_folder, filename)
        with open(filepath, 'rb') as f:
            raw_content = f.read()
        if ext in ['.html', '.htm']:
            templates_info[name] = smart_unicode(raw_content)
        elif ext == '.jade':
            templates_info[name] = convert_jade_to_html(raw_content)
    return templates_info


def build_api_templates():
    info = get_templates_info()
    info_string = '# coding: utf8\napi_templates = %s' % json.dumps(info, indent=4, ensure_ascii=False)
    info_filepath = templates_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'info.py')
    write_file(info_filepath, info_string)


if __name__ == '__main__':
    build_api_templates()

