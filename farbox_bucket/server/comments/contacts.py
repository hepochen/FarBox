#coding: utf8
from farbox_bucket.utils import smart_unicode, get_value_from_data
from farbox_bucket.server.comments.utils import get_comments



def get_contacts_from_comments(comments):
    # 从评论中获取name + email的字典  unicode
    # comments 是一个 dict 类型组成的 list
    contacts = dict()
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        author = comment.get('author')
        email = comment.get('email')
        if author and email:
            contacts[smart_unicode(author)] = email.lower()
    return contacts



def get_default_contacts_from_post(post):
    contacts = {}
    if isinstance(post, dict) and post.get('type') == 'post':
        from_address = get_value_from_data(post, 'metadata.from')
        from_author_name = get_value_from_data(post, 'metadata.author')
        if from_address and from_author_name:
            contacts[from_author_name] = from_address
    return contacts


def get_all_contacts_from_post(post, comments=None):
    if not post:
        return {}
    if comments is None:
        comments = get_comments(post)

    contacts = get_contacts_from_comments(comments) # it's a dict


     # 从 post 的 meta中处理, 一般都是 Bitcron Mail 产生的post，才有这样的属性
    contacts.update(get_default_contacts_from_post(post))

    # name 全部 lower 化，这样才能@的时候，不敏感
    lower_name_contacts = {smart_unicode(k).lower():v for k, v in contacts.items()}
    return lower_name_contacts



def get_contacts_from_new_comment(new_comment):
    # new_comment 是 web.utils.comment.add.NewComment 的实例化对象
    return get_all_contacts_from_post(new_comment.parent_obj)


