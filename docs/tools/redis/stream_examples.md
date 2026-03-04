Redis Stream Examples
basic config
redis_host = "redis"
stream_key = "skey"
stream2_key = "s2key"
group1 = "grp1"
group2 = "grp2"
connection
import redis
from time import time
from redis.exceptions import ConnectionError, DataError, NoScriptError, RedisError, ResponseError

r = redis.Redis( redis_host )
r.ping()
True
xadd and xread
add some data to the stream
for i in range(0,10):
    r.xadd( stream_key, { 'ts': time(), 'v': i } )
print( f"stream length: {r.xlen( stream_key )}")
stream length: 10
read some data from the stream
## read 2 entries from stream_key
l = r.xread( count=2, streams={stream_key:0} )
print(l)
[[b'skey', [(b'1710790167982-0', {b'ts': b'1710790167.9824948', b'v': b'0'}), (b'1710790167983-0', {b'ts': b'1710790167.9830241', b'v': b'1'})]]]
extract data from the returned structure
first_stream = l[0]
print( f"got data from stream: {first_stream[0]}")
fs_data = first_stream[1]
for id, value in fs_data:
    print( f"id: {id} value: {value[b'v']}")
got data from stream: b'skey'
id: b'1710790167982-0' value: b'0'
id: b'1710790167983-0' value: b'1'
read more data from the stream
if we call the xread with the same arguments we will get the same data

l = r.xread( count=2, streams={stream_key:0} )
for id, value in l[0][1]:
    print( f"id: {id} value: {value[b'v']}")
id: b'1710790167982-0' value: b'0'
id: b'1710790167983-0' value: b'1'
to get new data we need to change the key passed to the call

last_id_returned = l[0][1][-1][0]
l = r.xread( count=2, streams={stream_key: last_id_returned} )
for id, value in l[0][1]:
    print( f"id: {id} value: {value[b'v']}")
id: b'1710790167983-1' value: b'2'
id: b'1710790167983-2' value: b'3'
last_id_returned = l[0][1][-1][0]
l = r.xread( count=2, streams={stream_key: last_id_returned} )
for id, value in l[0][1]:
    print( f"id: {id} value: {value[b'v']}")
id: b'1710790167983-3' value: b'4'
id: b'1710790167983-4' value: b'5'
to get only newer entries

print( f"stream length: {r.xlen( stream_key )}")
# wait for 5s for new messages
l = r.xread( count=1, block=5000, streams={stream_key: '$'} )
print( f"after 5s block, got an empty list {l}, no *new* messages on the stream")
print( f"stream length: {r.xlen( stream_key )}")
stream length: 10
after 5s block, got an empty list [], no *new* messages on the stream
stream length: 10
to get the last entry in the stream

# read the last available message
l = r.xread( count=1, streams={stream_key: '+'} )
print(l)
print( f"stream length: {r.xlen( stream_key )}")
[[b'skey', [(b'1710790167984-0', {b'ts': b'1710790167.9839962', b'v': b'9'})]]]
stream length: 10
2nd stream
Add some messages to a 2nd stream

for i in range(1000,1010):
    r.xadd( stream2_key, { 'v': i } )
print( f"stream length: {r.xlen( stream2_key )}")
stream length: 10
get messages from the 2 streams

l = r.xread( count=1, streams={stream_key:0,stream2_key:0} )
for k,d in l:
    print(f"got from {k} the entry {d}")
got from b'skey' the entry [(b'1710790167982-0', {b'ts': b'1710790167.9824948', b'v': b'0'})]
got from b's2key' the entry [(b'1710790173142-0', {b'v': b'1000'})]