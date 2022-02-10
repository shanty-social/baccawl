local os = require('os')
local jwt = require('resty.jwt')
local key = os.getenv('JWT_KEY')
local data = ngx.req.get_body_data()

local obj = jwt:verify(key, data)
if not obj['valid'] then
    ngx.log(ngx.ERR, 'JWT verification failed: ' .. obj['reason'])
    ngx.exit(400)
end

local payload = obj['payload']
local clients = ngx.shared.clients

if payload['username'] == nil then
    ngx.log(ngx.ERR, 'JWT does not contain username')
    ngx.exit(400)
end
if payload['host'] == nil or payload['port'] == nil then
    ngx.log(ngx.ERR, 'JWT does not contain host and port')
    ngx.exit(400)
end

-- Record client connection info.
local conn = payload['host'] .. ':' .. payload['port']
if clients:get(payload['username']) == conn then
    ngx.log(ngx.INFO, 'Deregistering client: ' .. payload['username'] .. ', conn=' .. conn)
    clients:delete(payload['username'])
else
    ngx.log(ngx.ERR, 'Connection info mismatch')
    ngx.exit(400)
end

ngx.say('OK')
ngx.exit(200)
