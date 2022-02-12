local default = ngx.var.default;

-- Get hostname:
local host = ngx.req.get_headers()['Host']

-- TODO: hostname configurable...
local tunnels = ngx.shared.tunnels
local conn = tunnels:get(host)

if conn == nil then
    ngx.log(ngx.ERR, 'Could not lookup tunnel: ' .. host)
    return default
end

return 'http://' .. conn
