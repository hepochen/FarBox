#coding: utf8
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html

SEND_MESSAGE_WECHAT_TEMPLATE = convert_jade_to_html("""
xml
    ToUserName <![CDATA[{{request.xml.FromUserName}}]]>
    FromUserName <![CDATA[{{request.xml.ToUserName}}]]>
    CreateTime= now.format('%s')
    MsgType text
    Content <![CDATA[{{message}}]]>
    FuncFlag 0
""")


SEND_POSTS_WECHAT_TEMPLATE = convert_jade_to_html("""
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

