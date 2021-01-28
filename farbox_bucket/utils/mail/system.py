# coding: utf8
import datetime
from farbox_bucket.settings import SES_ID, SES_KEY, SES_SENDER
from farbox_bucket.utils.ssdb_utils import qpush_back
from .utils import send_email_by_amazon




def send_mail_by_system(to_address, content,  subject=None, raw=False):
    if not SES_KEY or not SES_ID:
        return False
    if len(content) > 1024*1024: # 内容过大了
        return False
    ses_id, ses_key = SES_ID, SES_KEY
    message_id = send_email_by_amazon(to_address=to_address, content=content, subject=subject, raw=raw,
                                      from_address=SES_SENDER, ses_id = ses_id, ses_key=ses_key)
    if not message_id:
        return False
    else:
        log_doc = dict(
            message_id = message_id,
            to_address = to_address,
            sent_at = datetime.datetime.utcnow(),
            subject = subject,
            raw = raw,
            content = content,
        )
        qpush_back('_system_mail_sender', log_doc)  # 记录日志
        return True

