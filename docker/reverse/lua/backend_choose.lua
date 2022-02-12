local default = ngx.var.default;

-- Get hostname:
local host = ngx.req.get_headers()['Host']
local path = ngx.var.request_uri

local clients = ngx.shared.backends

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
return default
