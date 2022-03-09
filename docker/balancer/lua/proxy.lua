local module = {}

local os = require('os')
local jwt = require('resty.jwt')
local key_file = os.getenv('JWT_KEY_FILE')
local tunnels = ngx.shared.tunnels
local key

local function read_file(path)
    local file = io.open(path, "rb") -- r read mode and b binary mode
    if not file then return nil end
    local content = file:read "*a" -- *a or *all reads the whole file
    file:close()
    return content
end

local function read_jwt(data)
    local obj = jwt:verify(key, data)
    if not obj['valid'] then
        ngx.log(ngx.ERR, 'JWT verification failed: ' .. obj['reason'])
        ngx.exit(400)
    end

    local payload = obj['payload']

    if payload['username'] == nil then
        ngx.log(ngx.ERR, 'JWT does not contain username')
        ngx.exit(400)
    end
    if payload['host'] == nil or payload['port'] == nil then
        ngx.log(ngx.ERR, 'JWT does not contain host and port')
        ngx.exit(400)
    end

    return payload
end

function module.init()
    -- Read JWT from file.
    key = read_file(key_file)
end

function module.add()
    local data = ngx.req.get_body_data()
    local payload = read_jwt(data)

    -- Record tunnel connection info.
    local conn = payload['host'] .. ':' .. payload['port']
    ngx.log(ngx.INFO, 'Registering tunnel: ' .. payload['username'] .. ', conn=' .. conn)
    for i, domain in ipairs(payload['domains']) do
        tunnels:set(domain, conn)
    end

    ngx.say('OK')
    ngx.exit(200)    
end

function module.del()
    local data = ngx.req.get_body_data()
    local payload = read_jwt(data)

    -- Record tunnel connection info.
    local conn = payload['host'] .. ':' .. payload['port']
    if tunnels:get(payload['username']) == conn then
        ngx.log(ngx.INFO, 'Deregistering tunnel: ' .. payload['username'] .. ', conn=' .. conn)
        for i, domain in ipairs(payload['domains']) do
            tunnels:delete(domain)
        end
    else
        ngx.log(ngx.ERR, 'Connection info mismatch')
        ngx.exit(400)
    end

    ngx.say('OK')
    ngx.exit(200)    
end

function module.find()
    -- Get hostname:
    local host = ngx.req.get_headers()['Host']
    local conn = tunnels:get(host)

    if conn == nil then
        ngx.log(ngx.ERR, 'Could not lookup tunnel: ' .. host)
        return ngx.var.default
    end

    return 'http://' .. conn
end

return module