#coding: utf8
from __future__ import absolute_import
import re
from flask import request
from urlparse import urlparse
from gevent import spawn
from farbox_bucket.settings import CAN_SEND_SYSTEM_EMAIL
from farbox_bucket.utils import is_email_address, smart_unicode
from farbox_bucket.bucket.utils import get_bucket_secret_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.private_configs import get_bucket_owner_email
from farbox_bucket.utils.mail.utils import pure_email_address
from farbox_bucket.utils.mail.system import send_mail_by_system
from .contacts import get_contacts_from_new_comment
from .template import get_comment_notification_content



def get_valid_emails(emails):
    valid_emails = []
    for email in emails:
        if not email:
            continue
        elif is_email_address(email):
            valid_emails.append(email.strip().lower())
    return list(set(valid_emails))  # 去重复


def get_people_to_notify(content):  # unicode,lower
    # 得到被 @ 的用户, 本身就是 username 类似的
    content = smart_unicode(content)
    persons = re.findall(u'@([^ #,，@:：\r\n\t]{1,30})', content)
    persons = [p.strip().lower() for p in persons if p.strip()]

    # 可能是 My Name 这种有空格形式的
    persons_blank = re.findall(u'@([^#,，@:：\r\n\t]{1,30})', content)
    for p in persons_blank:
        p = p.strip()
        if p not in persons: persons.append(p)

    _people = []
    for p in persons:
        p = p.strip()
        _people.append(p)
        if ' ' in p: # # 有可能是 `my name`这样的，被误判了
            _people += p.split()
    return _people



def get_contacts_from_comments(comments):
    # 从评论中获取name + email的字典  unicode,lower
    # comments 是一个 dict 类型组成的 list
    contacts = dict()
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        author = comment.get('author')
        email = comment.get('email')
        if author and email:
            contacts[smart_unicode(author).lower()] = email.lower()
    return contacts




def send_notification_emails(new_comment):
    if not CAN_SEND_SYSTEM_EMAIL:
        return
    if not new_comment.parent_obj or not isinstance(new_comment.parent_obj, dict):
        return #ignore
    people_to_notify = get_people_to_notify(new_comment.content)[:10] # 最多 10 个

    contacts = get_contacts_from_new_comment(new_comment)

    client_referrer = request.form.get('referrer')
    if client_referrer:
        if urlparse(client_referrer).netloc != urlparse(request.referrer).netloc: #或者来路的host跟client提交的不一致，不处理
            return
        else:
            parent_url = client_referrer
    else:
        parent_url = request.referrer
     # 没有来路的，不处理了
    if not parent_url:
        return


    emails = []
    for person in people_to_notify:
        person_email = contacts.get(person.lower().strip())
        if person_email and person_email not in emails:
            emails.append(person_email)
    emails = get_valid_emails(emails)

    # 需要通知的 emails 中增加站长自己的

    secret_site_configs = get_bucket_secret_site_configs(bucket=new_comment.bucket)
    admin_email = pure_email_address(secret_site_configs.get('email'), check=True)
    if admin_email and admin_email not in emails:
        emails.append(admin_email)

    # 通知 bucket 的所有者
    bucket = get_bucket_in_request_context() or request.values.get('bucket')
    bucket_owner_email = get_bucket_owner_email(bucket=bucket)
    if bucket_owner_email and bucket_owner_email not in emails:
        emails.append(bucket_owner_email)

    # 移除当前行为人自己的邮箱通知，自己做的事情自己清楚，没有必要通知
    if new_comment.email:
        new_comment_author_email = new_comment.email.strip().lower()
        try: emails.remove(new_comment_author_email)
        except: pass

    if not emails:
        return # ignore


    notification_content = get_comment_notification_content(comment_obj=new_comment, parent_obj=new_comment.parent_obj, current_link=parent_url)

    spawn(send_mail_by_system, to_address=emails, subject='New Comment', content=notification_content,)  # 异步处理

    request.emails_sent_info = "comment-%s-people" % len(emails)
    #send_mail_by_system(to_address=emails, subject='New Comment', content= notification_content,)







