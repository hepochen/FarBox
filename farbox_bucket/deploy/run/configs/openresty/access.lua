local log = ngx.log
local memcached = require "resty.memcached"
local memc, err = memcached:new()
if not memc then
    log(ngx.ERR, "failed to instantiate memc: ", err)
    return
end

memc:set_timeout(1000) -- 1 sec

local ok, err = memc:connect("127.0.0.1", 11211)
if not ok then
    log(ngx.ERR, "failed to connect: ", err)
    return
end

local client_ip = ngx.var.remote_addr

local ip_block_id = "block-" .. client_ip
local ip_block_value, flags, err = memc:get(ip_block_id)

if err then
    log(ngx.ERR, "memcached error: ", err)
    return
end

-- put it into the connection pool of size 100,
-- with 10 seconds max idle timeout
local ok, err = memc:set_keepalive(10000, 100)
if not ok then
    log(ngx.ERR, "cannot set keepalive: ", err)
end


if ip_block_value then
    ngx.exit(ngx.HTTP_FORBIDDEN)
end


