#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import to_unicode, to_md5, smart_unicode, string_types

from jinja2.loaders import  BaseLoader
from jinja2.environment import Template
from jinja2.utils import internalcode
from jinja2.exceptions import TemplateNotFound, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from jinja2.runtime import Undefined
from flask import abort, request
import datetime
import types

from farbox_bucket.server.template_system.model.text import Text
from farbox_bucket.server.template_system.model.date import Date

from farbox_bucket.server.template_system.template_system_patch import SafeUndefined, return_error_message
from farbox_bucket.server.utils.site_resource import get_template_source

from farbox_bucket.server.template_system.attr_patch import render_attr_func_without_call, patch_attr_func_for_obj



class FarboxBucketTemplateLoader(BaseLoader):
    def get_source(self, environment, template_name):
        template_source = get_template_source(template_name)
        if template_source:
            return template_source, template_name, lambda: True
        else:
            raise TemplateNotFound(template_name)

    @internalcode
    def load(self, environment, name, globals=None):
        globals = globals or {}
        source, filename, uptodate = self.get_source(environment, name)
        code = environment.compile(source, name, filename)
        template = environment.template_class.from_code(environment, code, globals, uptodate)
        template.source = source
        return template


def is_child_parent_repeated(child, parent, tree):
    # tree -> {child: parent}
    parent_parents = []
    raw_parent = parent
    max_times = len(tree)
    tried = 0
    while parent:
        tried += 1
        parent = tree.get(parent)
        if parent and parent not in parent_parents:
            parent_parents.append(parent)
        if tried > max_times:
            break
    if raw_parent in parent_parents: # 自己做了 parent
        return True
    if child in parent_parents:
        return True
    else:
        return False


def _get_is_string_or_number(value):
    if isinstance(value, (int, float)):
        return True
    elif isinstance(value, string_types):
        return True
    else:
        return False




class FarboxBucketEnvironment(SandboxedEnvironment): #  Environment
    intercepted_binops = frozenset(['**', '*', '/', '+'])
    def __init__(self, *args, **kwargs):
        kwargs['autoescape'] = False
        kwargs['auto_reload'] = False
        kwargs['cache_size'] = 50000
        kwargs['extensions'] = ['jinja2.ext.do']
        super(FarboxBucketEnvironment, self).__init__(*args, **kwargs)
        self.undefined = SafeUndefined
        self.loader =  FarboxBucketTemplateLoader()

    @staticmethod
    def template_not_found(name):
        content = return_error_message("template error: can't find the template named `%s`" % name)
        return Template(content)

    def get_template(self, name, parent=None, globals=None):
        if isinstance(name, Template):
            return name

        globals = self.make_globals(globals)
        name = name.strip('"\'')
        template_source = get_template_source(name)
        if template_source:
            template_md5_key = to_md5(template_source)
            template = self.cache.get(template_md5_key)
            if template is None:
                template = self.loader.load(environment=self, name=name, globals=globals)
                self.cache[template_md5_key] = template

            if parent:
                templates_tree = getattr(request, "templates_tree", {})
                if not isinstance(templates_tree, dict):
                    templates_tree = {}
                templates_tree[template.name] = parent # 记录 parent 的关系
                if is_child_parent_repeated(template.name, parent, templates_tree):
                    raise TemplateNotFound(name + "@repeated in a templates-loop!!!!!!")
                request.templates_tree = templates_tree

            if not parent:
                request.template_path = template.name

            return template
        else:
            is_parent = bool(not parent)
            if is_parent:
                raise TemplateNotFound(name)
            else:
                return self.template_not_found(name)



    def call_binop(self, context, operator, left, right):
        if isinstance(left, Undefined):
            left = ''
        if isinstance(right, Undefined):
            right = ''

        if isinstance(left, string_types) and isinstance(right, string_types):
            if operator in ['/', '//', '*', '**', '-']:
                return '%s%s%s' % (smart_unicode(left), operator, smart_unicode(right))

        if operator == '**':
            if left > 500 or right > 5:
                return self.undefined('the power operator is unavailable')
            else:
                return left**right
        elif operator == '+' and isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
            return list(left) + list(right)
        elif operator == '+' and isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        elif operator == '+' and _get_is_string_or_number(left) and _get_is_string_or_number(right):
            return '%s%s' % (left, right)
        else:
            # todo 这里要优化
            # 字符串的操作符是不允许的
            types = [type(left), type(right)]
            types = list(set(types)) # 去重
            if (left > 999999999999 or right > 999999999999) and\
                    not (isinstance(left, string_types) and isinstance(right, string_types)):
                return left or right
                #return self.undefined('the power operator is unavailable')
            elif len(types)==2 and (unicode in types or str in types) and (float in types or int in types): # 字符串的操作，如果是不同类型的，比如string*n是不允许的
                return ''
            elif operator == '/' and not right:
                # 会产生错误，除以0
                return ''
            else:
                return SandboxedEnvironment.call_binop(self, context, operator, left, right)


    def handle_exception(self, exc_info=None, rendered=False, source_hint=None):
        source_hint = source_hint or ''
        if not rendered:
            error = exc_info[1]
            filename = error.filename or ''
            if filename.endswith('.jade'):
                filename = '<a href="/service/template_code/%s">compiled %s</a>, ' \
                           'the line number may be different to your own code' % (filename, filename)
            error_information = "template file: %s \n line number:%s \n error message: %s" % (
                filename,
                error.lineno,
                error.message
            )
            error_info = dict(lineno=error.lineno, source=source_hint, message=error_information, debug=True)
            abort(500, error_info)
        elif exc_info[0] in [TemplateNotFound]:
            error_information = exc_info[1].message
            abort(500, error_information)
        elif exc_info[0] in [UndefinedError, ValueError, TypeError]:
            #sentry_client.captureException(exc_info)
            error_information = exc_info[1].message
            abort(500, error_information)
        else:
            # 这里不要尝试直接 500， 有可能是 redirect 或者其它错误
            return SandboxedEnvironment.handle_exception(self, exc_info, rendered, source_hint)


    def getattr(self, obj, attribute):
        if isinstance(obj, Undefined):
            return SafeUndefined()
        if attribute.startswith('__') or '.__' in attribute:  # !!! 不然会被注入
            return ''

        # 针对 doc 特殊的逻辑, 比如 comments 相关数据的获取
        #if isinstance(obj, dict) and obj.get('_type'): #  and attribute not in obj
        #    fake_value = get_value_for_fake_field_for_doc(obj, attribute)
        #    if fake_value is not None:
        #        return fake_value

        try_patch = False
        try:
            value = SandboxedEnvironment.getattr(self, obj, attribute)
            if isinstance(value, Undefined):
                try_patch = True
            elif hasattr(value, '__call__'):
                try_patch = True
        except UndefinedError:
            value = ''
            try_patch = True
        if isinstance(value, Undefined):
            try_patch = True

        if attribute.endswith('_'):
            try_Text = True
            attribute = attribute[:-1]
        else:
            if attribute in ['content']:
                try_Text = True
            else:
                try_Text = False

        if isinstance(value, datetime.datetime):
            return Date(value)
        elif isinstance(value, string_types) and try_Text:
            return Text(value, attr=attribute, parent=obj)

        # 必须被 patch 的一些属性
        if not try_patch and isinstance(obj, (Text, Date)) and not hasattr(obj, attribute):
            try_patch = True

        if value is None and attribute in ["cover"]:
            try_patch = True
        if not value and attribute in ["url"]:
            try_patch = True

        if try_patch:
            patched_func = patch_attr_func_for_obj(obj, attr=attribute)
            if patched_func is not None:
                return patched_func

        if hasattr(value, '__call__') and value and hasattr(obj, '__class__') and \
                isinstance(value, (types.FunctionType, types.MethodType)):
            # 只有默认变量的一些子属性才有这样的功能
            obj_class = obj.__class__
            if hasattr(obj_class, '__module__'):
                obj_module = obj_class.__module__
                if isinstance(obj_module, (str, unicode)) and '.namespace.' in obj_module:
                    value = render_attr_func_without_call(value)

        return value


farbox_bucket_env = FarboxBucketEnvironment()



def render_by_farbox_bucket_env(template_path, **kwargs):
    try:
        template = farbox_bucket_env.get_template(template_path)
        html = template.render(**kwargs)
    except:
        html = 'render error'
    return html
