local module = {}

local os = require('os')
local http = require('socket.http')
local ltn12 = require('ltn12')
local cjson = require('cjson')

local refresh_interval = os.getenv('BACKEND_REFRESH_INTERVAL')
if refresh_interval == nil then
    refresh_interval = 300
else
    refresh_interval = tonumber(refresh_interval)
end

local console_url = os.getenv('CONSOLE_URL')
local console_auth_token = os.getenv('CONSOLE_AUTH_TOKEN')

local backends = ngx.shared.backends
local url = console_url .. '/api/endpoints/'

function module.init()
    ngx.log(ngx.INFO, 'Refreshing backends')
    local r = {}
    local b, c, h = http.request({url = url,
        method = 'GET',
        headers = {
            ['Authorization'] = 'Bearer ' .. console_auth_token
        },
        sink=ltn12.sink.table(r)
    })

    if c ~= 200 then
        ngx.log(ngx.ERR, 'Status code ' .. c .. ' refreshing backends')
    else
        local endpoints = cjson.decode(table.concat(r, ''))

        for i, endpoint in ipairs(endpoints['objects']) do
            local domain_name = endpoint['domain']['name']
            local paths = backends:get(domain_name)
            if paths == nil then
                paths = {}
            end
            paths[endpoint['path']] = endpoint['host'] .. endpoint['http_port_internal']
            backends:set(domain_name, paths)
        end
    end

    ngx.timer.at(refresh_interval, module.init)
end

function module.choose()
    local host = ngx.req.get_headers()['Host']
    local path = ngx.var.request_uri

    local paths = backends:get(host)
    if paths == nil then
        ngx.log(ngx.ERR, 'Could not lookup backend: host=' .. host)
        return default
    end

    for i, prefix in ipairs(paths) do
        if path:find(prefix, 1, #prefix) then
            return paths[prefix]
        end
    end 

    ngx.log(ngx.ERR, 'Could not lookup backend: host=' .. host .. ', path=' .. path)
    return ngx.var.default
end

return module