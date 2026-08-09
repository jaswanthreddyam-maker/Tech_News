"""
Phase 2 Operational Activation — Step 1: Redis Key Investigation
READ-ONLY investigation of the editorial:v1:homepage_ranked_ids key.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

async def investigate_redis():
    from app.core.redis import get_redis_client
    redis = get_redis_client()
    
    key = "editorial:v1:homepage_ranked_ids"
    
    # Step 1: What type is the key?
    key_type = await redis.type(key)
    print(f"1. Redis TYPE of '{key}': {key_type}")
    
    # Step 2: What's stored in it?
    if key_type == b"string" or key_type == "string":
        val = await redis.get(key)
        print(f"2. Value (string): {val}")
    elif key_type == b"list" or key_type == "list":
        length = await redis.llen(key)
        vals = await redis.lrange(key, 0, -1)
        print(f"2. Value (list, len={length}): {[v.decode() if isinstance(v, bytes) else v for v in vals]}")
    elif key_type == b"hash" or key_type == "hash":
        vals = await redis.hgetall(key)
        decoded = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in vals.items()}
        print(f"2. Value (hash): {decoded}")
    elif key_type == b"set" or key_type == "set":
        vals = await redis.smembers(key)
        print(f"2. Value (set): {[v.decode() if isinstance(v, bytes) else v for v in vals]}")
    elif key_type == b"none" or key_type == "none":
        print("2. Key does not exist")
    else:
        print(f"2. Unknown type: {key_type}")
    
    # Step 3: Check TTL
    ttl = await redis.ttl(key)
    print(f"3. TTL: {ttl} (-1 = no expiry, -2 = key doesn't exist)")
    
    # Step 4: Check related keys
    all_editorial_keys = []
    async for k in redis.scan_iter(match="editorial:*"):
        key_name = k.decode() if isinstance(k, bytes) else k
        key_t = await redis.type(k)
        key_t_str = key_t.decode() if isinstance(key_t, bytes) else key_t
        all_editorial_keys.append((key_name, key_t_str))
    
    print(f"\n4. All editorial:* keys in Redis:")
    for kn, kt in sorted(all_editorial_keys):
        print(f"   {kn} -> type: {kt}")
    
    # Step 5: Check homepage cache keys
    homepage_keys = []
    async for k in redis.scan_iter(match="homepage:*"):
        key_name = k.decode() if isinstance(k, bytes) else k
        key_t = await redis.type(k)
        key_t_str = key_t.decode() if isinstance(key_t, bytes) else key_t
        homepage_keys.append((key_name, key_t_str))
    
    print(f"\n5. All homepage:* keys in Redis:")
    for kn, kt in sorted(homepage_keys):
        print(f"   {kn} -> type: {kt}")
    
    # Step 6: Check trending/news keys
    news_keys = []
    async for k in redis.scan_iter(match="news:*"):
        key_name = k.decode() if isinstance(k, bytes) else k
        key_t = await redis.type(k)
        key_t_str = key_t.decode() if isinstance(key_t, bytes) else key_t
        news_keys.append((key_name, key_t_str))
    
    print(f"\n6. All news:* keys in Redis:")
    for kn, kt in sorted(news_keys):
        print(f"   {kn} -> type: {kt}")

if __name__ == "__main__":
    asyncio.run(investigate_redis())
