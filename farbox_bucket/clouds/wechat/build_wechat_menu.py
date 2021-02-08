# coding: utf8
from farbox_bucket.clouds.wechat.utils.menu import create_menus


def create_menus_on_wechat():
    menus = {
        "button": [
            {
                "name": u"+图",
                "sub_button": [
                    {
                        "type": "pic_sysphoto",
                        "name": u"拍摄照片",
                        "key": "pic_sysphoto"
                    },
                    {
                        "type": "pic_weixin",
                        "name": u"本地照片",
                        "key": "pic_weixin"
                    },
                ],
            },
            {
                "name": u"管理",
                "sub_button": [
                    {
                        "type": "scancode_waitmsg",
                        "name": u"扫码绑定",
                        "key": "bind",
                    },
                    {
                        "type": "click",
                        "name": u"解除绑定",
                        "key": "unbind"
                    },
                    {
                        "type": "click",
                        "name": u"当前状态",
                        "key": "bind_status"
                    },
                ]
            },
            ]
    }

    return create_menus(menus)


if __name__ == '__main__':
    create_menus_on_wechat()