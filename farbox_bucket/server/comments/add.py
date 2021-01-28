#coding: utf8
from __future__ import absolute_import
import datetime, re
from flask import request, g, abort

from farbox_bucket.utils import smart_unicode, get_md5, get_value_from_data, is_email_address, to_float
from farbox_bucket.utils.memcache import cache_client
from farbox_bucket.utils.functional import cached_property

from farbox_bucket.bucket.domain.info import is_valid_domain

from farbox_bucket.bucket.utils import get_bucket_site_configs
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.server.utils.verification_code import is_verification_code_correct
from farbox_bucket.server.utils.request import safe_get, get_visitor_ip
from farbox_bucket.server.utils.response import jsonify
from farbox_bucket.server.template_system.api_template_render import render_api_template


from farbox_bucket.server.web_app import app

from .utils import get_comments_record, get_comments_by_comments_doc, get_comment_author_name, get_comment_avatar
from .dump import add_new_comment_to_doc


from .notification import send_notification_emails


class NewComment(object):
    def __init__(self):
        self.ip = get_visitor_ip()
        self.email = safe_get('email')
        self.site = safe_get('site')  # url, not just domain
        self.domain = request.form.get('site', '').lower().strip().replace('http://', '').replace('https://', '').strip('/')

        self.parent_path = request.values.get('path', '') # 所评论的文档路径

        self.utc_offset = to_float(self.parent_obj.get('_utc_offset'), default_if_fail=8)
        self.now = datetime.datetime.utcnow() + datetime.timedelta(0, self.utc_offset * 3600)
        self.date = self.now.strftime("%Y-%m-%d %H:%M:%S") # 用来构建 comment_id 的逻辑

        self.raw_comment_content = smart_unicode(request.form.get('content', '')) # 去掉html tag

        self.content =  self.raw_comment_content[:1000].strip() # 评论最多1k字

        self.error_info = ''

    @cached_property
    def bucket(self):
        return getattr(g, 'bucket', None) or request.values.get('bucket')

    @cached_property
    def id(self): # the comment id
        origin_id = '%s %s' % (self.email, self.date)
        return get_md5(origin_id)


    @cached_property
    def author(self):
        return get_comment_author_name(safe_get('author'), self.email)

    @cached_property
    def avatar(self):
        return get_comment_avatar(self.email)

    @cached_property
    def reply_id(self):
        reply_to = safe_get('reply') or '' # 这是一个 md5 后的 id
        if reply_to:
            for comment in self.all_comments:
                if comment.get('id') == reply_to:
                    # 获得原始的 reply_to_id, 这样才能进行存储
                    reply_to = comment.get('origin_id')
                    break
        return reply_to

    @cached_property
    def as_doc(self):
        doc = self.as_object.copy()
        doc['id'] = self.id
        doc['reply'] = self.reply_id
        doc['avatar'] = self.avatar
        return doc

    @cached_property
    def as_object(self):
        # 添加到 record.objects 中的数据
        doc = dict(
            site=self.site,
            email=self.email,
            date=self.date,
            author=self.author,
            ip=self.ip,
            content=self.content,
            reply=self.reply_id,
        )
        return doc


    def is_site_url_allowed(self):
        # 确认填入的 url 是否符合格式
        if self.domain:
            return is_valid_domain(self.domain)
        else: # 不填入网址目前是可以的
            return True

    @cached_property
    def post_method_is_allowed(self):
        if re.search(r'\[/\w+\]', self.content): # UBB语法的，认为是robot
            return False

        if not self.bucket or not self.parent_obj:
            return False

        # 10 分钟内，超过 5 次评论，认为是不允许的
        cache_key = '%s_comment' % self.ip
        block_times = cache_client.get(cache_key) or 0
        try:
            block_times = int(block_times)
        except:
            block_times = 0
        if block_times >= 5:
            return False
        else:
            cache_client.incr(cache_key, expiration=10*60)

        return True # at last


    ################# run on the web ######################

    def get_error_info(self):
        # 确认请求行为是否合法
        content_length = len(self.content)
        if content_length < 5:
            return u'min length of comment is 5!'

        if content_length > 5000:
            return u'max length of comment is 5000!'

        if not self.content:  # 编译后的评论内容为None
            return #ignore

        if not is_email_address(self.email): # 邮箱地址是必填的
            return u'email address missing.'

        if not self.is_site_url_allowed(): # 网站地址不对（如果填了的话）
            return u'site address format error!'

        v_code = (request.values.get('verification_code') or '').strip()
        if not v_code:
            return u'verification code is required'
        if len(v_code) !=4:
            return u'verification code length is 4'

        if not is_verification_code_correct(): # 验证码错误
            return u'verification code is error'

        if not self.post_method_is_allowed: # 当前请求
            return u'sorry, the comment system thought your behavior is like a robot. try again later?'

        blocked_info = u'sorry, this post is not allowed to post comment'

        # 很明显的 spam 特性
        if u'平台' in self.author or u'澳门' in self.author:
            return blocked_info
        elif u'共' in self.content and u'产' in self.content and u'党' in self.content:
            return blocked_info
        elif u'法' in self.content and u'轮' in self.content and u'功' in self.content:
            return blocked_info

        # 同ip, 同 email, 但是 site 不一样, 批量发广告的
        if self.email and self.ip and self.site:
            for old_comment in self.all_comments:
                if old_comment.get('ip')==self.ip and old_comment.get('email')==self.email and old_comment.get('site') != self.site:
                    return blocked_info

        if self.all_comments:
            last_comment = self.all_comments[-1]
            last_comment_content = last_comment.get('content') or ''
            if smart_unicode(last_comment_content) == self.content:
                return "can't comment same contents..."

    @cached_property
    def parent_obj(self):
        # comment.parent_path==post_path, 获得评论对应的数据对象（从数据库中）
        return get_record_by_path(self.bucket, self.parent_path) or {}

    @cached_property
    def comments_record(self):
        # objects 已经解密了
        record = get_comments_record(bucket=self.bucket, doc_path=self.parent_path)
        return record

    @cached_property
    def old_comments(self):
        record = self.comments_record or {}
        comments = record.get('objects') or []
        return comments

    @cached_property
    def all_comments(self): # 转义过得
        comments = get_comments_by_comments_doc(comments_doc=self.comments_record, as_tree=False, utc_offset=self.utc_offset)
        return comments




# 作为外部的 view 被调用的
def add_comment():
    # 最后返回一个 json 的字符串
    error = ''
    new_comment_instance = NewComment()
    if not new_comment_instance.parent_obj:
        error = 'no doc matched for comment'
    if not error:
        error = new_comment_instance.get_error_info()
    if error:
        return dict(error=error)

    # 更新到数据库的 chain 中
    old_comments = new_comment_instance.old_comments
    comments = [c for c in old_comments] # copy it
    comments.append(new_comment_instance.as_object)
    add_new_comment_to_doc(bucket=new_comment_instance.bucket,
                           parent_obj_doc=new_comment_instance.parent_obj,
                           comments = comments,
                           )

    # 进行邮件通知
    send_notification_emails(new_comment_instance)

    return new_comment_instance.as_doc



@app.route('/service/comment/new', methods=['POST'])
def add_new_comment_web_view():
    bucket = request.values.get("bucket")
    site_configs = get_bucket_site_configs(bucket)
    if not site_configs:
        comments_allowed = False
    else:
        comments_allowed = site_configs.get("comments")
    if not comments_allowed:
        abort(404, 'comment is not allowed in this site')
    new_comment_doc = add_comment()
    if new_comment_doc.get('error'): # 错误信息
        return jsonify(new_comment_doc)
    if request.values.get('format') in ['json', 'JSON']:
        return jsonify(new_comment_doc)
    else:
        return render_api_template('comment.jade', comment=new_comment_doc)
