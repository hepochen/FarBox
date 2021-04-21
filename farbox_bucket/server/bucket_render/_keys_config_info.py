# coding: utf8


builtin_site_settings_keys_config_info = {
    "wiki": {
        "title": "Settings for Wiki",
        "path": "__wiki.json",
        "note": "If you want to enable Wiki (which can be visited at the URL /wiki of current site), must set Wiki Root first! `Items of Homepage` can be a folder or a Markdown document, but both of them should be under the Wiki Root.",
        "keys": [
            "enable_wiki_nodes(type=bool, default=True)",
            "wiki_title(full_width=True, title='Title')",
            "wiki_root(full_width=True)",
            "categories(title='Custom Items of Homepage', type=dom_list, css_class=one_line, form_keys=[path,summary,icon(type=icon)])",
            "search_placeholder(placeholder=Search, full_width=True)", "_",
            "header_animation(type=bool, default=True)",
            "header_color(type=color,default=#0697dc)",
            "main_color(type=color,default=#0697dc)",
            "secondary_color(type=color,default=#cd5c5c)",
        ]
    },
    "wechat": {
        "title": "Settings for Wechat Account",
        "note": "if `Image Insert Type` set to `image`, the image synced will not insert into current Markdown document.",
        "path": "__wechat.json",
        "keys": [
            "post_folder(full_width=True)",
            "image_folder(full_width=True)",
            "-",
            "image_insert_type(full_width=True, type=select, placeholder='markdown_syntax@,image@')",
            "-",
            "silent_reply(type=bool, default=False)",
            "draft_by_default(type=bool, default=False)",
            "one_user_one_post(type=bool, default=False)",
            "user_post_per_day(type=bool, default=False)",
            "auto_add_date(type=bool, default=False)",
            "add_nickname(type=bool, default=False)",
        ]

    },
    "visit_passwords": {
        "title": "Passwords for Visiting",
        "private_keys": ["enable_visit_passwords", "visit_passwords"],
        "note": "url that starts with the `path` will ask visitor to input password to access, and do not use sensitive passwords, it will be be exposed in HTTP requests!",
        "keys": [
            "enable_visit_passwords(type=bool, default=True)",
            "visit_passwords(title='Rules', type=dom_list, css_class=one_line, form_keys=[path,password(type=input)])"
        ]
    },
    "site_images": {
        "title": "Background and Avatars",
        "path": "__site_images.json",
        "hide_submit_button": True,
        "keys": [
            'site_favicon(type=image, value=/_direct/favicon.ico, show_label=true, title=Site Favicon [.ico], hide_clear_action=true)',
			'avatar(type=image, value=/_direct/avatar.png, show_label=true, hide_clear_action=true)',
			'site_avatar(type=image, value=/_direct/site_avatar.png, show_label=true, hide_clear_action=true)', '-',
			'admin_avatar(type=image, value=/_direct/admin.png, show_label=true, hide_clear_action=true)',
			'visitor_avatar(type=image, value=/_direct/visitor.png, show_label=true, hide_clear_action=true)', '-',
			'default_background(type=image, value=/_direct/bg.jpg, full_width=true, show_label=true, hide_clear_action=true)',
        ]
    }
}
