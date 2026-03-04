Asyncio Examples
All commands are coroutine functions.

Connecting and Disconnecting
Using asyncio Redis requires an explicit disconnect of the connection since there is no asyncio deconstructor magic method. By default, an internal connection pool is created on redis.Redis() and attached to the Redis instance. When calling Redis.aclose this internal connection pool closes automatically, which disconnects all connections.

import redis.asyncio as redis

client = redis.Redis()
print(f"Ping successful: {await client.ping()}")
await client.aclose()
Ping successful: True
If you create a custom ConnectionPool to be used by a single Redis instance, use the Redis.from_pool class method. The Redis client will take ownership of the connection pool. This will cause the pool to be disconnected along with the Redis instance. Disconnecting the connection pool simply disconnects all connections hosted in the pool.

import redis.asyncio as redis

pool = redis.ConnectionPool.from_url("redis://localhost")
client = redis.Redis.from_pool(pool)
await client.aclose()
However, if the ConnectionPool is to be shared by several Redis instances, you should use the connection_pool argument, and you may want to disconnect the connection pool explicitly.

import redis.asyncio as redis

pool = redis.ConnectionPool.from_url("redis://localhost")
client1 = redis.Redis(connection_pool=pool)
client2 = redis.Redis(connection_pool=pool)
await client1.aclose()
await client2.aclose()
await pool.aclose()
By default, this library uses version 2 of the RESP protocol. To enable RESP version 3, you will want to set protocol to 3

import redis.asyncio as redis

client = redis.Redis(protocol=3)
await client.aclose()
await client.ping()
Transactions (Multi/Exec)
The aioredis.Redis.pipeline will return a aioredis.Pipeline object, which will buffer all commands in-memory and compile them into batches using the Redis Bulk String protocol. Additionally, each command will return the Pipeline instance, allowing you to chain your commands, i.e., p.set(‘foo’, 1).set(‘bar’, 2).mget(‘foo’, ‘bar’).

The commands will not be reflected in Redis until execute() is called & awaited.

Usually, when performing a bulk operation, taking advantage of a “transaction” (e.g., Multi/Exec) is to be desired, as it will also add a layer of atomicity to your bulk operation.

import redis.asyncio as redis

r = await redis.from_url("redis://localhost")
async with r.pipeline(transaction=True) as pipe:
    ok1, ok2 = await (pipe.set("key1", "value1").set("key2", "value2").execute())
assert ok1
assert ok2
Pub/Sub Mode
Subscribing to specific channels:

import asyncio

import redis.asyncio as redis

STOPWORD = "STOP"


async def reader(channel: redis.client.PubSub):
    while True:
        message = await channel.get_message(ignore_subscribe_messages=True, timeout=None)
        if message is not None:
            print(f"(Reader) Message Received: {message}")
            if message["data"].decode() == STOPWORD:
                print("(Reader) STOP")
                break

r = redis.from_url("redis://localhost")
async with r.pubsub() as pubsub:
    await pubsub.subscribe("channel:1", "channel:2")

    future = asyncio.create_task(reader(pubsub))

    await r.publish("channel:1", "Hello")
    await r.publish("channel:2", "World")
    await r.publish("channel:1", STOPWORD)

    await future
(Reader) Message Received: {'type': 'message', 'pattern': None, 'channel': b'channel:1', 'data': b'Hello'}
(Reader) Message Received: {'type': 'message', 'pattern': None, 'channel': b'channel:2', 'data': b'World'}
(Reader) Message Received: {'type': 'message', 'pattern': None, 'channel': b'channel:1', 'data': b'STOP'}
(Reader) STOP
Subscribing to channels matching a glob-style pattern:

import asyncio

import redis.asyncio as redis

STOPWORD = "STOP"


async def reader(channel: redis.client.PubSub):
    while True:
        message = await channel.get_message(ignore_subscribe_messages=True, timeout=None)
        if message is not None:
            print(f"(Reader) Message Received: {message}")
            if message["data"].decode() == STOPWORD:
                print("(Reader) STOP")
                break


r = await redis.from_url("redis://localhost")
async with r.pubsub() as pubsub:
    await pubsub.psubscribe("channel:*")

    future = asyncio.create_task(reader(pubsub))

    await r.publish("channel:1", "Hello")
    await r.publish("channel:2", "World")
    await r.publish("channel:1", STOPWORD)

    await future
(Reader) Message Received: {'type': 'pmessage', 'pattern': b'channel:*', 'channel': b'channel:1', 'data': b'Hello'}
(Reader) Message Received: {'type': 'pmessage', 'pattern': b'channel:*', 'channel': b'channel:2', 'data': b'World'}
(Reader) Message Received: {'type': 'pmessage', 'pattern': b'channel:*', 'channel': b'channel:1', 'data': b'STOP'}
(Reader) STOP
Sentinel Client
The Sentinel client requires a list of Redis Sentinel addresses to connect to and start discovering services.

Calling aioredis.sentinel.Sentinel.master_for or aioredis.sentinel.Sentinel.slave_for methods will return Redis clients connected to specified services monitored by Sentinel.

Sentinel client will detect failover and reconnect Redis clients automatically.

import asyncio

from redis.asyncio.sentinel import Sentinel


sentinel = Sentinel([("localhost", 26379), ("sentinel2", 26379)])
r = sentinel.master_for("mymaster")

ok = await r.set("key", "value")
assert ok
val = await r.get("key")
assert val == b"value"
Connecting to Redis instances by specifying a URL scheme.
Parameters are passed to the following schems, as parameters to the url scheme.

Three URL schemes are supported:

redis:// creates a TCP socket connection. https://www.iana.org/assignments/uri-schemes/prov/redis

rediss:// creates a SSL wrapped TCP socket connection. https://www.iana.org/assignments/uri-schemes/prov/rediss

unix://: creates a Unix Domain Socket connection.

import redis.asyncio as redis
url_connection = redis.from_url("redis://localhost:6379?decode_responses=True")
url_connection.ping()
True
To enable the RESP 3 protocol, append protocol=3 to the URL.

import redis.asyncio as redis

url_connection = redis.from_url("redis://localhost:6379?decode_responses=True&protocol=3")
url_connection.ping()