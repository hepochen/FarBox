#coding: utf8
from __future__ import absolute_import
from jinja2.runtime import Context, Undefined, Macro
from jinja2.compiler import CodeGenerator
from werkzeug.exceptions import HTTPException
from farbox_bucket.settings import DEBUG, sentry_client
from farbox_bucket.utils import smart_unicode, smart_str
from farbox_bucket.server.template_system.syntax_block import syntax_blocks
from farbox_bucket.server.template_system.namespace import namespace_functions, namespace_shortcuts
from farbox_bucket.server.template_system.namespace.record import get_records_for_request_resolver
from farbox_bucket.server.template_system.namespace.built_in import set_property
from .exceptions import TemplateDebugException
from jinja2.runtime import Undefined


def context_resolve(self, key):
    if key in self.vars:
        return self.vars[key]
    if key in self.parent:
        return self.parent[key]

    if key in syntax_blocks:
        return syntax_blocks[key]

    records_value = get_records_for_request_resolver(key)
    if records_value is not None:
        return records_value

    if key == 'set_property':
        return set_property

    # call the function to get namespace object
    if key in namespace_functions:
        func = namespace_functions[key]
        return func # do not call
    elif key in namespace_shortcuts:
        func = namespace_shortcuts[key]
        return func

    # at last
    return self.environment.undefined(name=key)





old_context_call = Context.call

def context_call(self, context_obj, *args, **kwargs):
    # 一般只是本地的 jade 才会调用到，外部的实际走evn_call
    if not hasattr(context_obj, '__call__'): # 不可 call, 可能仅仅是 property
        return context_obj
    if isinstance(context_obj, Undefined):
        return ''
    try:
        value = old_context_call(self, context_obj, *args, **kwargs)
        if value is None:
            value = Undefined()
        return value
    except HTTPException as e:
        raise  e
    except TemplateDebugException as e:
        raise e
    except TypeError as e:
        if hasattr(e, 'message') and 'not callable' in e.message:
            # 被调用的函数不可被call，返回原始值
            return context_obj
        else:
            # sentry_client.captureException()
            message = getattr(e, 'message', None) or ''
            if message:
                return message
            error_info = 'context_call error:* %s, ** %s; %s' % (smart_unicode(args), smart_unicode(kwargs), message)
            return error_info
    except Exception as e:
        if isinstance(context_obj, Macro):
            pass
        else:
            if sentry_client:
                sentry_client.captureException() # todo 目前这个错误还是会进行捕获

        message = getattr(e, 'message', None) or ''
        object_name = getattr(context_obj, '__name__', None) or ''
        if DEBUG:
            print 'context_call error\n', context_obj, args, kwargs
        if message:
            error_info = message
        else:
            error_info = 'context_call error: %s, * %s, ** %s; %s' % (object_name, smart_unicode(args), smart_unicode(kwargs), message)

        return '<error>%s</error>' % error_info




old_visit_name_func = CodeGenerator.visit_Name
def visit_name(self, node, frame):
    try:
        # for jinja2 old version
        hit =  node.name not in frame.identifiers.declared_locally or node.ctx=='load'
    except:
        hit = node.ctx=='load'

    if node.name in namespace_functions and hit:
        # 默认变量最终转化为 call 的模式，因为本身就是函数，这样不会改变模板内代码整体的执行次序
        try:
            ref = frame.symbols.ref(node.name)
        except:
            # for jinja2 old version context.resolve(node.name)
            ref = 'l_%s' % node.name
        self.write("environment.call(context, %s)" % ref)
    else:
        old_visit_name_func(self, node, frame)




def patch_context():
    Context.resolve = context_resolve
    Context.resolve_or_missing = context_resolve

    Context.call = context_call
    CodeGenerator.visit_Name = visit_name


############


def return_error_message(message):
    if 'error_ignored' in message:
        error_info = ''
    else:
        error_info = '<span style="color:red" class="template_api_error">&lt;%s&gt:</span>' % message
    return error_info




class SafeUndefined(Undefined):
    # 直接融入到用户的API渲染的页面中，我们自己程序中不做callback
    def __init__(self, *args, **kwargs):
        self._empty_list = []
        Undefined.__init__(self, *args, **kwargs)

    def __iter__(self):
        return self._empty_list.__iter__()

    def _fail_with_undefined_error(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self

    __add__ = \
    __radd__ = \
    __getitem__ = \
    __sub__ = \
    __mul__ = \
    __div__ = \
    __lt__ = \
    __le__ = \
    __gt__ = \
    __ge__ = _fail_with_undefined_error

    def __call__(self, *args, **kwargs):
        if self._undefined_name in ['caller', 'join', 'json', 'content']:
            return ''
        return return_error_message('`%s` is not a valid function' % self._undefined_name)


    def __repr__(self):
        return 'SafeUndefined'