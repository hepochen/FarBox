#!/bin/bash
docker run -d \
 -p 7788:80 -p 443:443 -p 80:80 \
 -v /home/run/$name$/configs:/mt/web/configs \
 -v /data/log/$name$:/mt/web/log \
 -v /data/$name$:/mt/web/data \
 -v /data/$name$_ssdb:/mt/ssdb/data \
 -v /static/$name$:/mt/web/static \
 -v /log/docker:/mt/docker/log \
 hepochen/farbox_bucket:latest