REDIS_DELETE_ACKED_MESSAGES = """
local stream = KEYS[1]
local group = ARGV[1]

-- Get pending message IDs
local pending = redis.call("XPENDING", stream, group, "-", "+", 10000)
local pending_ids = {}
for i, v in ipairs(pending) do
    pending_ids[v[1]] = true
end

-- Get all stream IDs
local all = redis.call("XRANGE", stream, "-", "+")
local deleted = 0

for i, entry in ipairs(all) do
    local id = entry[1]
    if not pending_ids[id] then
        redis.call("XDEL", stream, id)
        deleted = deleted + 1
    end
end

return deleted
"""
