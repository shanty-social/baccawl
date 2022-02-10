local default = ngx.var.default;

-- Get hostname:
local host = ngx.req.get_headers()['Host']

-- TODO: hostname configurable...
local host = host:match('([0-9%a%u-]+).shanty.local')
local clients = ngx.shared.clients
local conn = clients:get(host)

if conn == nil then
    ngx.log(ngx.ERR, 'Could not lookup client: ' .. host)
    return default
end

return 'http://' .. conn
