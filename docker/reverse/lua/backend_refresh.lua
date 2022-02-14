local os = require('os')
local http = require('socket.http')
local ltn12 = require('ltn12')
local cjson = require('cjson')

local REFRESH_INTERVAL = os.getenv('BACKEND_REFRESH_INTERVAL')
if REFRESH_INTERVAL == nil then
    REFRESH_INTERVAL = 300
else
    REFRESH_INTERVAL = tonumber(REFRESH_INTERVAL)
end

local CONSOLE_URL = os.getenv('CONSOLE_URL')
local CONSOLE_AUTH_TOKEN = os.getenv('CONSOLE_AUTH_TOKEN')

local backends = ngx.shared.backends
local url = CONSOLE_URL .. '/api/endpoints/'

function get_backends()
    ngx.log(ngx.INFO, 'Refreshing backends')
    local r = {}
    local b, c, h = http.request({url = url,
        method = 'GET',
        headers = {
            ['Authorization'] = 'Bearer ' .. CONSOLE_AUTH_TOKEN
        },
        sink=ltn12.sink.table(r)
    })

    if c != 200 then
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

    ngx.timer.at(REFRESH_INTERVAL, get_backends)
end

get_backends()
