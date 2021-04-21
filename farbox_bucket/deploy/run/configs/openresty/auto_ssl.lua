local log = ngx.log
local ssl = require "ngx.ssl"
local http = require "resty.http"
local resty_lock = require "resty.lock"
local server_name = ssl.server_name()
local key, cert, cert_type


if not server_name then
    return
end


-- just ip
if string.find(server_name, "%d+%.%d+%.%d+%.%d+") then
    return
end


-- Local cache related
local cert_cache = ngx.shared.cert_cache
local cert_cache_duration = 7200 -- 2 hours

key  = cert_cache:get(server_name .. "_k")
cert = cert_cache:get(server_name .. "_c")

-- hit the cache
if key ~= nil and cert ~= nil then
    ssl.set_der_cert(cert)
    ssl.set_der_priv_key(key)
    return
end


local lock = resty_lock:new("auto_ssl_locks", {exptime=60, timeout=0.1} )

-- lock first, by server_name
if lock then
    local elapsed, err = lock:lock(server_name)
end


local httpc = http.new()
httpc:set_timeout(8000)
httpc:connect("unix:/tmp/web_server.sock");

local res, err = httpc:request {
    path = "/_system/install_ssl/" .. server_name,
    headers = {
        ["Host"] = '127.0.0.1'
    },
}

if res then
    local res_body, err = res.read_body(res)
    if err then
        log(ngx.ERR, "res_body error ", err)
    elseif res.status==200 then
        key, cert = res_body:match("([^,]+),([^,]+)")
        if key ~= nil and cert ~= nil then
            -- Set cert
            local der_cert, err = ssl.cert_pem_to_der(cert)
            local ok, err = ssl.set_der_cert(der_cert)
            if not ok then
                log(ngx.ERR, "failed to set DER cert: ", err)
                return
            else
                cert_cache:set(server_name .. "_c", der_cert, cert_cache_duration)
            end

            -- Set key
            local der_key, err = ssl.priv_key_pem_to_der(key)
            local ok, err = ssl.set_der_priv_key(der_key)
            if not ok then
                log(ngx.ERR, "failed to set DER key: ", err)
                return
            else
                cert_cache:set(server_name .. "_k", der_key, cert_cache_duration)
            end
        else
            if res_body == "wait" then
                log(ngx.ERR, "wait for issuer")
            else
                log(ngx.ERR, "key or cert not work because of request error for " .. server_name)
            end
        end
    end
else
    log(ngx.ERR, "failed to request cert: ", err)
end


-- unlock now
if lock then
    local ok, err = lock:unlock()
    if not ok then
        ngx.say("failed to unlock: ", err)
    end
    ngx.say("unlock: ", ok)
end

httpc:set_keepalive(10000, 100)