#coding: utf8
from __future__ import absolute_import
import sys, os
from farbox_bucket.utils.console_utils import get_args_from_console, get_first_arg_from_console
from farbox_bucket.utils.cli_color import print_with_color
from farbox_bucket.client.project import show_projects, show_project, get_project_config, set_project_node
from farbox_bucket.client.message import send_message_for_project


# farbox_bucket <project_name> <action>

# farbox_bucket projects
# farbox_bucket project <xxxx>
# farbox_bucket set_<project> --node=<node>
# farbox_bucket set_<project> --domain=<-domain>

def main():
    raw_args = sys.argv[2:]
    kwargs, args = get_args_from_console(raw_args, long_opts=['project=', 'node=', 'domain='])
    node = kwargs.get('node') or ''
    node = node.strip()
    domain = kwargs.get('domain') or ''
    if node: # set remote node to POST/GET
        os.environ['DEFAULT_NODE'] = node
    action = get_first_arg_from_console()
    if action == 'projects':
        show_projects()
    elif action == 'project':
        if args:
            show_project(args[0])
        else:
            print_with_color('farbox_bucket project <xxxx>')
    elif action.startswith('set_'):
        project = action.split('_', 1)[-1].strip()
        project_config = get_project_config(project)
        if not project_config:
            print_with_color('no project named %s' % project)
        else:
            if node:
                set_project_node(project, node)
                show_projects()
            elif domain:
                domain = domain.strip().lower()
                if domain.startswith('-'):
                    action = 'unregister'
                    domain = domain.strip('-')
                else:
                    action = 'register'
                send_message_for_project(project, message=dict(domain=domain), action=action)

    else:
        print_with_color('no command matched')


if __name__ == '__main__':
    main()

