#coding: utf8


SEND_MESSAGE_WECHAT_TEMPLATE = """<xml>
  <ToUserName><![CDATA[%s]]></ToUserName>

  <FromUserName><![CDATA[%s]]></FromUserName>

  <CreateTime>%s</CreateTime>

  <MsgType>text</MsgType>

  <Content><![CDATA[%s]]></Content>

  <FuncFlag>0</FuncFlag>

</xml>"""