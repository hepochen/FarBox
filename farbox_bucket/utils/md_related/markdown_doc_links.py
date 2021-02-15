# coding: utf8
import re
from farbox_bucket.utils import smart_unicode, is_a_markdown_file, string_types


def get_link_title_id_in_wiki_syntax(line):
    # 已经去除头尾的 [[ 与 ]] 了
    # 要考虑有多个 | ，多个 # 的情况...
    # get_link_title_id_in_wiki_syntax("hello")
    # get_link_title_id_in_wiki_syntax("hello | title #id")
    # get_link_title_id_in_wiki_syntax("hello #id |title")
    # get_link_title_id_in_wiki_syntax("hello #more |title # id | title2")
    line = smart_unicode(line.strip())
    if line.startswith("#"):
        line = line[1:]
        is_tag = True
    else:
        is_tag = False
    link_id_c = re.search("#([^#|]+)(\||$)", line)
    if link_id_c:
        link_id = link_id_c.group(1).strip()
    else:
        link_id = ""
    link_title_c = re.search("\|([^#|]+)(#|$)", line)
    if link_title_c:
        link_title = link_title_c.group(1).strip()
    else:
        link_title = ""
    link_parts = re.split("[#|]", line)
    if link_parts:
        link = link_parts[0].strip()
    else:
        link = ""
    if is_tag:
        link = "#" + link
    return link, link_title, link_id


def get_linked_docs_from_markdown_content(path, raw_content, md_link_abs_check_func=None):
    # return [unicode]
    if not raw_content:
        return [],[]
    if not isinstance(raw_content, string_types):
        return [],[]
    raw_content = smart_unicode(raw_content)

    # [xxx](/???.md)
    maybe_md_links = []
    for m in re.finditer("(?:(?<=^)|(?<!!))(\\[.*?\\])\\((.*?)\\)", raw_content):
        link = m.group(2)
        if "://" in link:
            continue
        if "?" in link:
            link = link.split("?")[0]
        if "#" in link and not link.startswith("#"):
            link = link.split("#", 1)[0]
        link = link.strip()
        if is_a_markdown_file(link): # here, must be a markdown file
            if not link in maybe_md_links:
                maybe_md_links.append(link)


    for m in re.finditer("(?<!\[)(\[\[)([^\[\]]+)(\]\])", raw_content):
        # [[ xxx ]]
        # [[ xxx | title ]]
        # [[ xxx | title # id ]]
        link = m.group(2)
        link, link_title, link_id = get_link_title_id_in_wiki_syntax(link)
        if "?" in link:
            link = link.split("?")[0]
        if "#" in link and not link.startswith("#"):
            link = link.split("#", 1)[0]
        if not link:
            continue
        link = link.strip()
        if link not in maybe_md_links:
            maybe_md_links.append(link)


    # 校验
    tags = []
    post_parent_path = path.strip("/").rsplit("/", 1)[0]
    link_paths = []
    for maybe_md_link in maybe_md_links:
        if maybe_md_link.startswith("#"):
            tag = maybe_md_link.lstrip("#")
            if tag not in tags:
                tags.append(tag)
            continue
        if not is_a_markdown_file(maybe_md_link): # by default add .md ext to the link
            maybe_md_link += ".md"
        if maybe_md_link.startswith("/"): # 相对于根目录下已经是完整的地址了
            link = maybe_md_link
        else:
            if md_link_abs_check_func and md_link_abs_check_func(maybe_md_link):
                # 函数判断，可以省略了 /， 但此时又进行了补全
                link = "/%s" % maybe_md_link.strip("/")
            else:
                link = "%s/%s" % (post_parent_path, maybe_md_link.strip("/"))
        if not link:
            continue

        # 全小写化处理
        link = link.lower().lstrip("/")

        if link not in link_paths:
            link_paths.append(link)

    return link_paths, tags



