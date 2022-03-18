local os = require('os')

local SSHD_HOSTS = os.getenv('SSHD_HOSTS')
local TUNNELS_MAP = os.getenv('TUNNELS_MAP') or '/usr/local/etc/haproxy/tunnels.map'

-- Good reference:
-- http://www.arpalert.org/src/haproxy-lua-api/2.6/index.html
-- LUA fiddle:
-- https://www.lua.org/cgi-bin/demo

function split(s, sep)
    if sep == nil then
        sep = "%s"
    end
    local t = {}
    for str in string.gmatch(s, "([^"..sep.."]+)") do
            table.insert(t, str)
    end
    return t
end

local function fetch_tunnels(addr)
    local addr_p = split(addr, ':')
    core.Debug('Connected to: ' .. addr)

    local s = core.tcp()
    s:connect(addr_p[1], tonumber(addr_p[2]))
    local r = s:receive('*a')
    core.Debug('Read ' .. string.len(r) .. ' bytes')
    s:close()
    return split(r, '\n')
end

function update_tunnels()
    -- TODO: remove me, this is for testing...
    core.set_map(TUNNELS_MAP, 'localhost', '172.25.0.200')

    while true do
        core.Debug("Updating tunnel map.\n")

        for _, host_def in ipairs(split(SSHD_HOSTS, ',')) do
            core.Debug('Updating host: ' ... host_def)
            local tunnels = fetch_tunnels(host, port)
    
            for _, tunnel in ipairs(tunnels) do
                core.Debug(' - Adding domain: ' .. tunnel)
                core.set_map(TUNNELS_MAP, tunnel, host)
            end
        end
    
        core.msleep(5000)
    end
end

core.Info('Registering update_tunnels task for map: ' .. TUNNELS_MAP)
core.register_task(update_tunnels)
