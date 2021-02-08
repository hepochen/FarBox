# coding: utf8
import os

def do_install_project_log_rotate(force=False):
    config_folder = "/etc/logrotate.d"
    if not os.path.isdir(config_folder):
        return
    project_log_rotate_config_filepath = os.path.join(config_folder, "farbox_bucket")
    if not force and os.path.isfile(project_log_rotate_config_filepath):
        return
    project_log_rotate_content = """/mt/web/log/nginx_web_server.access.log {
        rotate 7
        size 5k
        dateext
        dateformat -%Y-%m-%d
        missingok
        compress
        sharedscripts
        postrotate
            test -r /var/run/nginx.pid && kill -USR1 `cat /var/run/nginx.pid`
        endscript
    }
    """
    with open(project_log_rotate_config_filepath, "wb") as f:
        f.write(project_log_rotate_content)


def install_project_log_rotate(force=False):
    try:
        do_install_project_log_rotate(force=force)
    except:
        pass