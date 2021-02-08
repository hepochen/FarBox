# coding: utf8
import os
from farbox_bucket.utils import string_types, get_value_from_data
from farbox_bucket.utils.path import is_sub_path, get_just_name, get_relative_path

# input -> raw_posts_info:
# links: {
#  "paths": {}
#  "links": {}
# }
# tags: {
#  "paths": {}
#  "tags": {}
# }


# output ->
# {
#  "nodes": [
#       {"id": "id1", "name": "name1", "val": 1}
#  ],
# "links": [
#       { "source": "id1", "target": "id2" }
# ]
# }



def filter_and_get_posts_link_points_info(posts_info, under=""):
    under = under.strip("/").strip().lower()
    links_info = get_value_from_data(posts_info, "links.links")
    if not isinstance(links_info, dict): links_info = {}
    tags_info = get_value_from_data(posts_info, "tags.tags")
    if not isinstance(tags_info, dict): tags_info = {}

    output_nodes = []
    output_nodes_map = {}
    output_links = []
    filepath_counter = {}
    filepath_group_info = {} # hit parent, +5

    for tag, tagged_paths in tags_info.items():
        valid_count = 0
        tag_node_id = "#%s" % tag
        for path in tagged_paths:
            if under and not is_sub_path(path, under):
                continue
            else:
                filepath_counter[path] = filepath_counter.get(path, 0) + 1
                valid_count += 1
                if path not in output_nodes_map:
                    path_node = dict(id=path, name=get_just_name(path), group=2)
                    output_nodes.append(path_node)
                    output_nodes_map[path] = path_node
                # create node-link
                if tag_node_id != path:
                    output_links.append(dict(source=tag_node_id, target=path))
        if not valid_count:
            continue
        tag_node = dict(
            id = tag_node_id,
            name = tag,
            val = valid_count,
            group = 1,
        )
        output_nodes.append(tag_node)
        output_nodes_map[tag_node_id] = tag_node


    for source_path, linked_paths in links_info.items():
        if under and not is_sub_path(source_path, under):
            continue
        valid_count = 0
        for path in linked_paths:
            if under and not is_sub_path(path, under):
                continue
            else:
                filepath_counter[path] = filepath_counter.get(path, 0) + 1
                valid_count += 1
                if path not in output_nodes_map:
                    path_node = dict(id=path, name=get_just_name(path), group=2)
                    output_nodes.append(path_node)
                    output_nodes_map[path] = path_node
                # create node-link
                if source_path != path:
                    output_links.append(dict(source=source_path, target=path))
        if not valid_count:
            continue
        if source_path not in output_nodes_map:
            path_node = dict(id=source_path, name=get_just_name(source_path), group=2)
            output_nodes.append(path_node)
            output_nodes_map[source_path] = path_node


    # update path nodes count
    for path, count in filepath_counter.items():
        path_node = output_nodes_map.get(path)
        if path_node:
            path_node["val"] = count

    for node in output_nodes:
        node_id = node.get("id")
        if node_id.startswith("#"):
            continue
        relative_path = get_relative_path(node_id.lower(), under.lower(), return_name_if_fail=False)
        if relative_path:
            level1_parent = relative_path.split("/")[0]
            if level1_parent not in filepath_group_info:
                group_id = len(filepath_group_info) + 5
                filepath_group_info[level1_parent] = group_id
            else:
                group_id = filepath_group_info[level1_parent]
            node["group"] = group_id


    output = {
        "nodes": output_nodes,
        "links": output_links,
    }

    return output



