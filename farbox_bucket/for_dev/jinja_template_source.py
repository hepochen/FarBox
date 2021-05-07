# coding: utf8
from jinja2.sandbox import SandboxedEnvironment
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html

def get_jinja_source_code_from_jade(jade_content, with_lines=True):
    source_code_lines = []
    html_content = convert_jade_to_html(jade_content)
    env = SandboxedEnvironment()
    #env.compile(html_content)
    source = env._parse(html_content, None, None)
    python_code = env._generate(source, None, None, False)
    python_lines = python_code.split("\n")
    for (i, python_line) in enumerate(python_lines):
        if with_lines:
            source_code_lines.append("%s:%s" % (i+1, python_line))
        else:
            source_code_lines.append(python_line)
    return "\n".join(source_code_lines)


def print_jinja_source_code_from_jade_file(jade_filepath):
    with open(jade_filepath) as f:
        jade_content = f.read()
    source_code = get_jinja_source_code_from_jade(jade_content, with_lines=True)
    print(source_code)