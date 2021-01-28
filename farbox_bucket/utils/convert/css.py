#coding: utf8
from scss import Scss
from scss.errors import SassSyntaxError
compiler = Scss()
import os, re
try:
    import gevent
except:
    gevent = None


def compile_css(content, filename=None, hash_key=None, cache_client=None):
    # 计算 cache_key
    if hash_key and cache_client:
        cache_key = 'css:%s' % hash_key
        cached = cache_client.get(cache_key, zipped=True)
        if cached:
            return cached
    else:
        cache_key = None

    raw_content = content
    if filename and isinstance(filename, (str, unicode)):
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in ['.less']:
            content = re.sub(r'@(\w)', '$\g<1>', content)
            content = re.sub(r'\$media ', '@media ', content)
    # remove import tag
    content = re.sub(r'@import.*?[\r\n]', '', content, re.I)
    try:
        to_return = compiler.compile(content)
    except SassSyntaxError, e:
        try:
            message = str(e)
            to_return = '/*%s*/\n%s' % (message, raw_content)
        except:
            to_return = raw_content
    except Exception, e:
        to_return = raw_content

    # cache it
    if cache_key and cache_client:
        cache_client.set(cache_key, to_return, zipped=True)

    return to_return


def compile_css_with_timeout(content, filename=None, hash_key=None, cache_client=None, timeout=2):
    if not gevent:
        return
    gevent_job = gevent.spawn(compile_css, content, filename, hash_key, cache_client)
    try:
        content = gevent_job.get(block=True, timeout=timeout)
    except:
        content = ''
        gevent_job.kill(block=False)
    return content
