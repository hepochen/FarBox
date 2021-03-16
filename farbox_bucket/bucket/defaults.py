#coding: utf8

# 基础结构
zero_id = '0'*24 # 创世ID, 一旦创建，不可修改
zero_id_for_user = '0'*23 + '1'  # 用户的设定，会进行加密
zero_id_for_site = '0'*23 + '3' # site configs
zero_id_for_secret = '0'*23 + '4' # secret site configs，也会进行加密

# 基础数据
zero_id_for_pages = '0'*23 + '2'
zero_id_for_files = '0'*23 + '6'
zero_id_for_posts = '0'*23 + '7'

# 变动支持
zero_id_for_histories = '0'*22 + '11'
zero_id_for_statistics = '0'*22 + '12'
zero_id_for_orders = '0'*22 + '13'  # 配合 zero_id_for_files
zero_id_for_inbox = '0'*22 + '14'

# todo 变动区域分为两种类型，一个是整个 bucket 内保持同步的（如何处理冲突呢？），一个是只在当前 node 生效的
# todo 倾向于只有一种，就是只在当前 node 生效的


# 主要是外部调用 get_records 查询的时候，给一个基准 id，可以避免 zero_ids 被查询到
# 主要是模板引擎中调用
zero_id_for_finder = '0'*22 + '99'

zero_ids = [zero_id, zero_id_for_user, zero_id_for_site, zero_id_for_secret,
            zero_id_for_pages, zero_id_for_files, zero_id_for_posts,
            zero_id_for_histories, zero_id_for_statistics,
            zero_id_for_orders, zero_id_for_inbox]


bucket_config_doc_id_names = {
    'init': zero_id,
    'user': zero_id_for_user,
    'site': zero_id_for_site,
    'secret': zero_id_for_secret,
    'pages': zero_id_for_pages,
    'files': zero_id_for_files,
    'posts': zero_id_for_posts,
    'histories': zero_id_for_histories,
    'statistics': zero_id_for_statistics,
    'orders': zero_id_for_orders,
    'inbox': zero_id_for_inbox,
}

config_names_not_allowed_set_by_user = ['init', 'histories', 'statistics', 'inbox']



BUCKET_RECORD_SORT_TYPES = ('post', 'image', 'file', 'folder', 'comments')

BUCKET_RECORD_SLASH_TYPES = ('post', 'image', 'file', 'folder', 'comments', "visits")