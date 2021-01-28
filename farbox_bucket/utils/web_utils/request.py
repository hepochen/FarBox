# coding: utf8


def to_per_page(per_page, new_per_page=None, min_per_page=1, max_per_page=1000):
    if new_per_page:
        # 如果有设定 new_per_page， 会尝试以其为高优先级
        try: per_page = int(new_per_page)
        except: pass
    if per_page < min_per_page:
        per_page = min_per_page
    if per_page > max_per_page:
        per_page = max_per_page
    return per_page
