local os = require('os')

local SSHD_BACKEND = os.getenv('SSHD_BACKEND') or 'sshd';
local TUNNELS_MAP = os.getenv('TUNNELS_MAP') or '/usr/local/etc/haproxy/tunnels.map'

-- Good reference:
-- http://www.arpalert.org/src/haproxy-lua-api/2.6/index.html
-- LUA fiddle:
-- https://www.lua.org/cgi-bin/demo

-- Utility function -- split string on separator.
local function split(s, sep)
    local t = {}

    if sep == nil then
        sep = "%s"
    end
    for str in string.gmatch(s, "([^"..sep.."]+)") do
        table.insert(t, str)
    end
    return t
end

-- Utility function -- return size of table.
local function count(T)
    local count = 0
    for _ in pairs(T) do count = count + 1 end
    return count
end

-- Fetch tunnels from sshd.
local function fetch_tunnels(addr)
    core.Debug('Connecting to: ' .. addr)

    local s = core.tcp()
    s:connect(addr)
    local r = s:receive('*a')
    s:close()

    if r == nil then
        core.Debug('Empty reply')
        return
    end

    core.Debug('Read ' .. string.len(r) .. ' bytes')
    return split(r, '\n')
end

-- Update tunnels from single sshd server.
local function update_server_tunnels(addr)
    core.Debug('Updating server: ' .. addr)
    local host = split(addr, ':')[1]
    local tunnels = fetch_tunnels(host .. ':1337')

    if tunnels == nil then
        core.Debug('No tunnels, skipping server...')
        return
    end

    local tunnel_count = count(tunnels)
    core.Debug('Retrieved ' .. tunnel_count .. ' tunnels')

    for _, tunnel in ipairs(tunnels) do
        core.Debug(' - Adding domain: ' .. tunnel)
        core.set_map(TUNNELS_MAP, tunnel, host)
    end
end

-- Endless loop that updates domain router map.
local function update_tunnels()
    -- Pause a little while for dns updates...
    core.msleep(5000)

    while true do
        core.Debug('Updating tunnel map.\n')

        local backend = core.backends[SSHD_BACKEND]
        if backend ~= nil then
            core.Debug('Enumerating backend: ' .. SSHD_BACKEND)

            for name, server in pairs(backend.servers) do
                core.Debug('Discovered server: ' .. name)
                local addr = server:get_addr()
                if addr ~= '<unknown>' then
                    update_server_tunnels(addr)
                end
            end
        end

        core.msleep(60000)
    end
end

core.Info('Registering update_tunnels task for map: ' .. TUNNELS_MAP)
core.register_task(update_tunnels)
