# coding: utf8
import os
from farbox_bucket.client.dump_template import get_template_info
from farbox_bucket.utils import to_bytes

root = os.path.abspath(os.path.dirname(__file__))

themes_py_file = os.path.join(root, '__init__.py')


templates = {}

for name in os.listdir(root):
    folder_path = os.path.join(root, name)
    if not os.path.isdir(folder_path):
        continue
    template_key = name.lower().strip()
    template_info = get_template_info(folder_path)
    template_info['_theme_key'] = template_key
    templates[template_key] = template_info


py_file_content = '#coding: utf8\nthemes = %s' % templates
with open(themes_py_file, 'wb') as f:
    f.write(to_bytes(py_file_content))




