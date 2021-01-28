# coding: utf8
from __future__ import absolute_import
from flask import render_template_string, request
from utils.convert import jade2jinja

SEND_MESSAGE_WECHAT_TEMPLATE = jade2jinja.exchange("""
xml
    ToUserName <![CDATA[{{request.xml.FromUserName}}]]>
    FromUserName <![CDATA[{{request.xml.ToUserName}}]]>
    CreateTime= now.format('%s')
    MsgType text
    Content <![CDATA[{{message}}]]>
    FuncFlag 0
""")


SEND_POSTS_WECHAT_TEMPLATE = jade2jinja.exchange("""
xml
    ToUserName <![CDATA[{{request.xml.FromUserName}}]]>
    FromUserName <![CDATA[{{request.xml.ToUserName}}]]>
    CreateTime= now.format('%s')
    MsgType news
    ArticleCount= posts.length
    Articles
        for post in posts
            item
                Title <![CDATA[{{post.title}}]]>
                Description <![CDATA[{{post.content.limit(80).no_pic_no_html}}]]>
                img_get_vars = 'width=640&height=640&outbound_link_password='+get_outbound_link_password(days=7)
                if post.cover
                    PicUrl <![CDATA[http://{{site._domain}}{{post.cover}}?{{img_get_vars}}]]>
                elif loop.index==1
                    PicUrl <![CDATA[http://{{site._domain}}/farbox_free_image.jpg?{{img_get_vars}}]]>
                Url <![CDATA[http://{{site._domain}}{{post.url}}#main]]>
""")



def send_wechat_message(message):
    # 被动地发送文本信息，即响应微信API的请求
    # set_content_type('application/xml')
    return render_template_string(SEND_MESSAGE_WECHAT_TEMPLATE, message=message)


def send_wechat_posts(posts):
    try:
        posts = list(posts)[:5]
    except:
        return # ignore
    if not posts:
        # 没有日志可以发送
        return send_wechat_message('Sorry, there is no post for now.')

    #set_content_type('application/xml')
    return render_template_string(SEND_POSTS_WECHAT_TEMPLATE, posts = posts)
