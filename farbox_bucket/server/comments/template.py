# coding: utf8
from jinja2 import Template


comment_notification_template_source = u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
    <title>New Comment</title>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
</head>
<body>
    <div style="font-size: 14px; max-width:720px;font-family: 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; letter-spacing: 1px; margin: 30px auto 50px auto;-webkit-text-size-adjust:none; border-radius:5px;border: 1px solid #ddd;">
        <div id="head" style="padding: 0 10px; height:38px; border-radius:5px; border-bottom-left-radius: 0 0;border-bottom-right-radius: 0 0; background: #ababab; text-align: right;">
            <div id="caption" style="color: #fafafa; line-height: 2.5;font-size: 16px;">
                New Comment
            </div>
        </div>

        <div style="line-height: 1.9;font-size: 13px;color:#555;padding: 10px 15px 0 15px; margin: 0 10px">

            <p>Hey,</p>


            <p><b>{{ comment.author }}</b> ({{comment.email}}) Said on <a href="{{ link }}" style="text-decoration: none; color: #333;">{{ parent.title }}</a></p>

            <div>

                {{ comment.content }}

            </div>


            <div style="text-align: right">
                <a href="{{ link }}" style="color: #008aff;">&gt;visit and reply comment</a>
            </div>


            <hr style="margin-top:35px;border:none; border-bottom: 1px solid #eee; height: 1px;"/>

            <p style="font-size: 10px">
                simple is everything, we try our best to make the Tech meet the needs of our lives.
            </p>

        </div>
        <div>

        </div>
    </div>
</body>
</html>"""


comment_notification_template = None
def get_comment_notification_template():
    global comment_notification_template
    if not comment_notification_template:
        comment_notification_template = Template(comment_notification_template_source)
    return comment_notification_template



def get_comment_notification_content(comment_obj, parent_obj, current_link):
    template = get_comment_notification_template()
    html = template.render(link=current_link, parent=parent_obj, comment=comment_obj)
    return html


