#coding: utf8
import os, subprocess, tempfile
try:
    import gevent
except:
    gevent = None

def get_bin_script():
    scripts = [
        '/usr/local/bin/coffee',
        '/usr/bin/coffee',
        '/usr/local/share/npm/bin/coffee'
        ]
    for bin_script in scripts:
        if os.path.isfile(bin_script):
            return bin_script

COFFEE_SCRIPT = get_bin_script()


def compile_coffee(raw_content):
    if isinstance(raw_content, unicode):
        raw_content = raw_content.encode('utf8')
    temp = tempfile.NamedTemporaryFile()
    temp.file.write(raw_content)
    temp.file.close()

    command = 'cat %s | %s -sc' % (temp.name, COFFEE_SCRIPT)
    try:
        js_content = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    except:
        js_content = raw_content
    temp.close()
    return js_content

def is_coffee_valid():
    if 'call(this)' in compile_coffee('number = -42 if opposite'):
        return True
    else:
        return False


def compile_coffee_with_timeout(raw_content, timeout=2):
    if not gevent:
        return
    gevent_job = gevent.spawn(compile_coffee, raw_content)
    try:
        content = gevent_job.get(block=True, timeout=timeout)
    except:
        content = ''
        gevent_job.kill(block=False)
    return content


