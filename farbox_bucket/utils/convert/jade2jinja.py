#coding: utf8
from pyjade.utils import process
from pyjade import Compiler as _Compiler
from pyjade.parser import Parser
from pyjade.lexer import Lexer
import re, os
from farbox_bucket.utils import to_unicode
from jinja2 import Template


def re_exclude_split(text, split_str, exclude_rules=None, maxsplit=0):
    # 某段 text 按照split_str分割成 list，但是某个正则规则内（比如括号内的）的split_str 则不能计算在内
    # split_str = ':'
    attrs_parts = []
    if exclude_rules is None:
        exclude_rules =  [
            (r'\(.*?\)'),
            (r'\[.*?\]'),
            (r'".*?"'),
            (r"'.*?'"),
        ]# '[\(\[\"\'].*?[\]\)\"\']'
    if exclude_rules: # like ['\(.*?\)', ]
        for exclude_rule in exclude_rules:
            for i in re.finditer(exclude_rule, text):
                attrs_parts += range(i.start(), i.end())

    split_parts = [] # 括号内的 : 是不能用于分割的
    split_count = 0
    for split_found in re.finditer(split_str, text):
        if split_found.start() not in attrs_parts:
            split_parts.append(split_found.start())
            split_count += 1
            if maxsplit and split_count >= split_count:
                break

    parts = []
    if split_parts:
        indexes_parts = zip([0]+split_parts, split_parts+[len(text)])
        for i,j in indexes_parts:
            part = text[i:j]
            sub_pattern = split_str
            if not sub_pattern.startswith('^'):
                sub_pattern = '^'+sub_pattern
            part = re.sub(sub_pattern, '', part) # 清除参与分割的字符串
            parts.append(part)

    return parts


class JadCompilerError(Exception):
    pass

lexer_init = Lexer.__init__

def _lexer_init(self, *args, **kwargs):
    lexer_init(self, *args, **kwargs)
    self.RE_ATTR_INTERPOLATE = re.compile(r'#\{([^{}]+)\}')

    # 避免有';'的时候，被隔断，例如： row_style = 'background:url(%s);'%row.bg.value
    self.RE_ASSIGNMENT = re.compile(r'^(-\s+var\s+)?(\w+) += *([^\n]+)( *;? *)')

Lexer.__init__ = _lexer_init

parseExpr = Parser.parseExpr

def _parser_except(self, type):
    t = self.peek().type
    if t == type:
        return self.advance()
    else:
        raw_content = re.sub(r'\r\n|\r', '\n', self.input)
        compiled_content = self.input[:raw_content.rfind(self.lexer.input)]
        line_number = re.sub(r'\s+$', '', compiled_content).count('\n') + 1
        raise JadCompilerError('expected "%s" but got "%s" on line %d' %  (type, t, line_number))

def _parseExpr(self):
    t = self.peek().type
    try:
        return parseExpr(self)
    except Exception, e:
        if not isinstance(e, JadCompilerError):
            raw_content = re.sub(r'\r\n|\r', '\n', self.input)
            compiled_content = self.input[:raw_content.rfind(self.lexer.input)]
            line_number = re.sub(r'\s+$', '', compiled_content).count('\n') + 1
            raise JadCompilerError('unexpected token "%s" on line %d'  %  (t, line_number))
        else:
            raise e


Parser.parseExpr = _parseExpr
Parser.expect = _parser_except


ONE_LINE_FUNCTIONS = ['load', 'set_content_type', 'redirect', 'a_with_selected', 'set_per_page', 'add_doc_actions', 'make_site_live']
DEFAULT_NAMES = ['request','response', 'doc','post', 'posts', 'site', 'sites', 'files', 'tags', 'tag', 'folder', 'folders',
                    'category', 'images', 'albums', 'album', 'next_one', 'pre_one', 'paginator', 'pager']


block_or_re_pattern = 'page|scroll|font|browser|pure|footer|create_dom|modal|tab' # block 语法

class Compiler(_Compiler):
    def __init__(self, node, **options):
        _Compiler.__init__(self, node, **options)
        self.current_line = 0

    def visit(self, node, *args, **kwargs):
        result = _Compiler.visit(self, node, *args,**kwargs)
        if hasattr(node, 'line') and node.line != self.current_line:
            self.current_line = node.line
            self.buffer('\n')
        return result

    def buffer(self,strs):
        if strs.startswith('{%'):
            strs=  '\n%s\n' % strs
        _Compiler.buffer(self, strs)

    def visitText(self,text):
        text = ''.join(text.nodes)
        text = self.interpolate(text)
        self.buffer(text) # 不用补充 \n 了，在visit 函数中会自动处理

    def visitCodeBlock(self,block):
      self.buffer('{%% block %s %%}'%block.name)
      if block.mode=='append': self.buffer('%ssuper()%s' % (self.variable_start_string, self.variable_end_string))
      self.visitBlock(block)
      if block.mode=='prepend': self.buffer('%ssuper()%s' % (self.variable_start_string, self.variable_end_string))
      self.buffer('{% endblock %}')

    def visitTag(self, tag):
        name = tag.name
        if name in DEFAULT_NAMES or (name.startswith('_') and len(name)>1):
            # 相当于按照我们自己的声明，调用 backend 的某个属性或者函数
            # 这些tag的，可以处理不带函数的变量
            # not tag.attrs 就是单纯一个变量的调用....
            #  {'name': 'class', 'static': True, 'val': u'"bcd tbc"'}]
            var_name_list = [name.lstrip('_')]
            if not tag.attrs: # 单纯变量调用，没有子属性，也不可能是函数调用
                self.buffer('{{ %s }}' % '.'.join(var_name_list))
            else: # tag.attrs 是有序的 list
                attrs = []
                class_attr = None
                for attr in tag.attrs:
                    if attr.get('name') == 'class': # 子属性的调用实际上是
                        class_attr = attr
                    else:
                        attrs.append(attr)
                if class_attr:
                    var_name_list += class_attr.get('val', '').strip('"\'').split(' ') # 原始会被视为 classes
                var_real_name = '.'.join(var_name_list)

                # 可能是赋值
                text_notes = getattr(getattr(tag, 'text', None), 'nodes', None)
                if text_notes and len(text_notes) == 1:
                    text = text_notes[0].strip()
                    if len(text) >=2 and text[0]=='=' and text[1]!='=':
                        # 实际上赋值行为
                        if '.' not in var_real_name:
                            return self.buffer('{%% set %s = %s %%}' % (var_real_name,text[1:]))
                        else: # 子属性的赋值是 jinja 不支持的，所以调用一个公用函数 set_property 这非常重要！
                            parent_obj_name = '.'.join(var_name_list[:-1])
                            property_name = var_name_list[-1]
                            return self.buffer('{{ set_property(%s, "%s", %s) }}' % (parent_obj_name, property_name, text[1:]))

                self.buffer('{{ %s }}' % var_real_name)

        elif name in ['from'] and hasattr(tag, 'text') and hasattr(tag.text, 'nodes') and len(tag.text.nodes)==1:
            # from xxx import 类似的，
            sub_text = tag.text.nodes[0].strip()
            parts = re.split(' +', sub_text, 1)
            if len(parts)==2 and '"' not in parts[1] and "'" not in parts[1]:
                p1, p2 = parts
                current_line = '{%% from "%s" %s %%}' %(p1.strip('\'"'), p2)
                self.buffer(current_line)
            else:
                return _Compiler.visitTag(self, tag)
        else:
            return _Compiler.visitTag(self, tag)

    def visitMixin(self,mixin):
        if not mixin.call:
            self.buffer('{%% macro %s(%s) %%}'%(mixin.name,mixin.args))
            self.visitBlock(mixin.block)
            self.buffer('\n{% endmacro %}\n')
        else:
            if not mixin.block:
                self.buffer('{{ %s(%s) }}' % (mixin.name, mixin.args))
            else:
                self.buffer('{%% call %s(%s) %%}'%(mixin.name,mixin.args))
                self.visitBlock(mixin.block)
                self.buffer('\n{% endcall %}\n')


    def visitAssignment(self,assignment):
        self.buffer('{%% set %s = %s %%}'%(assignment.name, assignment.val))

    def interpolate(self,text):
        return self._interpolate(text,lambda x:'{{ %s }}' % x)

    def visitVar(self, var, escape=False):
        var = self.var_processor(var)
        return '{{ %s }}' % var

    def visitEach(self,each):
        self.buf.append("{%% for %s in %s %%}"%(','.join(each.keys), each.obj))
        self.visit(each.block)
        self.buf.append('{% endfor %}')


    def visitDynamicAttributes(self,attrs):
        buf = ''
        for attr in attrs:
            buf += ' %s="{{%s}}" ' % (attr['name'], attr['val'])
        self.buf.append(buf)


#FEED_HTML = '\n<link rel="alternate" type="application/rss+xml" title="atom 1.0" href="/feed">\n'
CONTENT_TYPE_HTML = '\n<meta http-equiv="content-type" content="text/html; charset=utf-8">\n'




def beautiful_jade(source):
    # 先处理跨行的，合并为单行
    source = re.sub(r'\\[\t \r]*\n\s*', '', source)

    # 跨行的赋值处理
    multi_lines_vars = re.findall('{%[\t \r\n].*?[\t \r\n]%}', source, re.S|re.M)
    for multi_lines_var in multi_lines_vars:
        if '\n' in multi_lines_var:
            source = source.replace(multi_lines_var, re.sub(r'[\r\n]', '', multi_lines_var), 1)

    source = source.replace('\r\n', '\n')
    source = re.sub(r'\t', '    ', source) # 替换掉 tab 键为空格
    raw_lines = re.split(r'\n|\r', source)
    lines = []
    raw_pre_space_count = 0 # 原始文本的上行空格数
    space_count_added_points = {} # 因为 : 分行的原因，在某个缩进位置产生的行首叠加
    # {4:8} 表示在第一个4格缩进的时候，增加了8个 offset，在下载4格缩进或者更小的情况下，清空这个 point
    # {4:4,  8:4} 意味着实际在8+4的位置上，是 4+4的偏移

    in_special_block = False # like style or script
    special_block_space = 0 # 开始进入的节点


    for line_i, line in enumerate(raw_lines):
        # 去除了括号内的内容的 line，这样比较容易判断 dom 本身的结构
        line_without_attrs = re.sub(r'\(.*?\)', '', line).strip()
        line_strip = line.strip()

        if not line_strip: # 空行，不做处理, 不然会影响缩进的计算
            lines.append(line)
            continue

        # 获得行首空格的数目, 先集成之前行的
        space_count = raw_pre_space_count

        space_c = re.search(r'^ +', line)
        if space_c:
            raw_space_count = space_count = len(space_c.group())
        else:
            raw_space_count = 0


        # 一些特殊代码块进入的状态判断
        if raw_space_count > raw_pre_space_count:
            # 自级
            if line_i:
                pre_line = raw_lines[line_i-1]
                if re.match(r'\s*(style|script)(\(|\s*$)', pre_line) and not in_special_block:
                    # 一些特殊节点下面的，不再做split_colon 的处理
                    in_special_block = True
                    special_block_space = raw_pre_space_count
        else:
            if raw_space_count <= special_block_space:
                in_special_block = False
                special_block_space = 0


        #print line, in_special_block


        points = space_count_added_points.items()
        offset = 0
        for space_count_added_at, space_count_added_offset in points:
            if raw_space_count <= space_count_added_at:
                space_count_added_points.pop(space_count_added_at, None)
            else:
                offset += space_count_added_offset

        if raw_pre_space_count >= raw_space_count:
            #上行的缩进多余当前行，当前 level 相当于另起一行了，使用raw_space_count
            space_count = raw_space_count

        # 偏差性移动
        space_count += offset

        force_split_colon = False
        split_colon = False # 将 : 替换被必要的换行
        if re.search(r'(^| )(if|for|else|elif) .*?: ', line) or re.search(r': (if|for|else|elif) ', line):
            split_colon = True
        elif re.match('[a-z0-9\s]+:\s*\+[^)]*?\)\s*$', line_strip): #like ->  li: +h.a(xxxxx) -> one `()` only
            split_colon = True
            force_split_colon = True
        elif re.match(r'([\.#]?[a-z])', line_without_attrs, re.I) and ":" in line_without_attrs \
                and re.search(r'[a-z0-9](= [\'"].*?[\'"])?$', line_without_attrs, re.I):
            # 该行是 dom 结构的父子关系的声明，不是a= v or a = v 之类的, 也不是 +, _开头的函数调用和变量调用
            # 当然 post:xxxx 这种形式不要出现，作为变量的 post，在此时就是语法冲突的
            # li: a= post.title 这个是可以的
            split_colon = True
        elif re.match(r'\+(%s)(\(.*?\))?\s*:'%block_or_re_pattern, line_strip): # 代码块语法的，也允许冒号进行分割
            split_colon = True
        if split_colon: # 不分割的特殊情况
            if re.search(r'style\s*=', line): # style 申明 in one line
                split_colon = False
            elif in_special_block:
                split_colon = False

        if split_colon and not force_split_colon:
            if re.match(r'if |else\s*:|elif |else if ', line_strip): # 逻辑判断的，必须分割
                pass
            elif ('+' in line and not line_strip.startswith('+')) or ' = ' in line:
                # 可能是一些变量里比如 style，带来 : , 为了避免麻烦
                split_colon = False

        if split_colon:
            # post_url = 'http://' + request.host + post.url.escaped  这个就不算: 能分割的了
            dom_parts = re_exclude_split(line_strip, ':')
            dom_parts = [part.lstrip() for part in dom_parts]

            if dom_parts:
                # 记录偏移点，实际当前位置是不会增加偏移的，只会继承之前的偏移
                space_count_added_points[raw_space_count] = 4 * (len(dom_parts)-1)
                for dom_part in dom_parts:
                    lines.append(' '*space_count+dom_part)
                    space_count += 4
            else: # 实际上没有缩进
                lines.append(' '*space_count+line_strip)
        else:
            # 多变量赋值
            if ', ' in line_strip and ' = ' in line_strip and line_strip.count(', ')+1 == line_strip.count(' = '):
                sub_lines = line_strip.split(', ')
                for sub_line in sub_lines:
                    sub_line = sub_line.strip()
                    if not sub_line: continue
                    lines.append(' '*space_count+sub_line)
            else: #rest 获得新的 space_count 组成新的 line
                lines.append(' '*space_count+line_strip)


        # at last
        raw_pre_space_count = raw_space_count

    new_lines = []
    for line in lines:
        # 全局通用的变量空间
        global_types = 'posts|images|request|response'
        # todo + category & etc

        line_strip = line.strip()
        if line_strip.startswith('///'):
            # 完全注释，都不会出现在 html 的代码中
            continue
        elif line_strip.startswith('+'):
            # 函数的调用，不管是全局变量，都改成 jinja 先
            # 比如 +category.set('text', category['title']) 就会不认...
            # 变量的调用也可以用+的形式来
            if line_strip[1:] in ['caller']:
                new_line = line
            elif not re.match('\+\w+\(.*?\)$', line_strip) and not re.match('\+(%s)'%block_or_re_pattern, line_strip):
                # 非函数调用需要属性的（call），非 pure 等 block 代码语法，自动处理为变量先
                new_line = re.sub(r'(\s*)(\+)(\w+.*)', '\g<1>{{ \g<3> }}', line)
            else:
                #  +xxx()  这种纯 call 的，直接返回，可能是 mixin 的内部
                new_line = line
        else:
            # 函数的调用，这里会以)结尾; 预先转为 jinja 模式，不然在 jade 里没有办法解析

            # by default
            new_line = line
            done = False

            # 可能是 title= xxx 这种前后端结合的模式， 比如下面的例子，虽然又 posts.tag..join('+')， 但不能把它单独{{}} 起来
            # title= posts.keywords or post.title or posts.tags.join('+') or posts.category.title or site.title
            if line.count('= ') == 1 and ' = ' not in line:
                front_part, end_part = new_line.split('= ')
                front_part_strip = front_part.strip()
                if (re.match(r'\w+$', front_part_strip) or re.match(r'\w+\(.*?\)$', front_part_strip)) \
                        and not end_part.strip().startswith('{{'):
                    new_line = front_part + '{{ %s }}' % end_part
                    done = True

            if not done and not re.match(r'\s*\w+(\.\w+)? = ', line) and not re.search('%s\.\w+\s*\}\}' % global_types, line):
                # 替换全局变量名
                # 但不能是   xx = xx 这种赋值类型的
                # 也不能是 a(target="_blank", href="http://{{request.domain}}") 类似已经处理了的
                new_line = re.sub(r'(\s*)(_)?(%s)(\..*?\)\s*)' % global_types, '\g<1>{{ \g<3>\g<4> }}', line)



        new_lines.append(new_line)

    new_source = '\n'.join(new_lines)


    # 语法 block 的特别处理
    new_source = re.sub(r'(^ *|\n *)\+(%s)( *\n)' % block_or_re_pattern, '\g<1>+\g<2>()\g<3>', new_source)

    return new_source





def convert_jade_to_html(source, hash_key=None, cache_client=None):
    # 计算 cache_key
    if hash_key and cache_client:
        cache_key = 'jade:%s' % hash_key
        cached = cache_client.get(cache_key, zipped=True)
        if cached:
            return cached
    else:
        cache_key = None

    source = to_unicode(source)
    source = source.strip().replace(u'\ufeff', '') #去除头尾

    source = re.sub(r'\\\r?\n', '', source) # 多行分割合并成一行的对应

    #source = re.sub(r'\t', '    ', source) # 替换掉 tab 键为空格
    source = beautiful_jade(source)

    source = re.sub(r'((?:^|\n) *)else if ', '\g<1>elif ', source) # 替换else if->elif

    for func_name in ONE_LINE_FUNCTIONS:
        # 对单行特定函数，先处理为template的语法
        source = re.sub(r'([\r\n] *|^ *)(%s\(.*?\))(?= *[\r\n]|$)'%func_name, '\g<1>{{\g<2>}}', source) # 对单行的load函数的处理，避免被当成一个TagName

    new_source = process(source, compiler=Compiler)

    # 对头部代码的补充处理
    head_codes_search = re.search(r'<head>.*?</head>', new_source, re.S)
    if head_codes_search and 'set_content_type(' not in new_source: # 如果有设定content_type的，就不额外处理了
        if not new_source.startswith('<!'):
            new_source = "<!DOCTYPE html>\n"+new_source
        head_codes = head_codes_search.group()
        #if not re.search(r'<link.*?rel=["\']alternate["\']', head_codes, re.I): # 增加feed链接
        #    new_source = new_source.replace('<head>', '<head>%s' % FEED_HTML)
        if not re.search(r'<meta.*?http-equiv=[\'"]content-type[\'"]', head_codes, re.I): # 增加content_type声明
            new_source = new_source.replace('<head>', '<head>%s' % CONTENT_TYPE_HTML)

    # cache it
    if cache_key and cache_client:
        cache_client.set(cache_key, new_source, zipped=True)

    return new_source



def jade_to_template(source, env=None):
    compiled_source = convert_jade_to_html(source)
    if env: # 指定了某个 env 的
        template = env.from_string(compiled_source)
    else:
        template = Template(compiled_source)
    template.source = compiled_source
    return template



def compile_file(in_path):
    if not os.path.isfile(in_path):
        return
    if not in_path.endswith('.jade'):
        return
    out_path = in_path.replace('.jade', '.html')
    with open(in_path) as f:
        source_code = f.read()
    compiled_code = convert_jade_to_html(source_code)
    if isinstance(compiled_code, unicode):
        compiled_code = compiled_code.encode('utf8')
    with open(out_path, 'w') as f:
        f.write(compiled_code)


if __name__ == '__main__':
    print(beautiful_jade("""
    li: +h.a('Get on App Store', href='https://apps.apple.com/cn/app/markdown-app/id1483287811?l=en&mt=12', target='_blank')
    """))