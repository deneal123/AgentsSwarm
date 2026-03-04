Stream groups
With the groups is possible track, for many consumers, and at the Redis side, which message have been already consumed. ## add some data to streams Creating 2 streams with 10 messages each.

def add_some_data_to_stream( sname, key_range ):
    for i in key_range:
        r.xadd( sname, { 'ts': time(), 'v': i } )
    print( f"stream '{sname}' length: {r.xlen( stream_key )}")

add_some_data_to_stream( stream_key, range(0,10) )
add_some_data_to_stream( stream2_key, range(1000,1010) )
stream 'skey' length: 20
stream 's2key' length: 20
use a group to read from the stream
create a group grp1 with the stream skey, and

create a group grp2 with the streams skey and s2key

Use the xinfo_group to verify the result of the group creation.

## create the group
def create_group( skey, gname ):
    try:
        r.xgroup_create( name=skey, groupname=gname, id=0 )
    except ResponseError as e:
        print(f"raised: {e}")

# group1 read the stream 'skey'
create_group( stream_key, group1 )
# group2 read the streams 'skey' and 's2key'
create_group( stream_key, group2 )
create_group( stream2_key, group2 )

def group_info( skey ):
    res = r.xinfo_groups( name=skey )
    for i in res:
        print( f"{skey} -> group name: {i['name']} with {i['consumers']} consumers and {i['last-delivered-id']}"
              + f" as last read id")

group_info( stream_key )
group_info( stream2_key )
skey -> group name: b'grp1' with 0 consumers and b'0-0' as last read id
skey -> group name: b'grp2' with 0 consumers and b'0-0' as last read id
s2key -> group name: b'grp2' with 0 consumers and b'0-0' as last read id
group read
The xreadgroup method permit to read from a stream group.

def print_xreadgroup_reply( reply, group = None, run = None):
    for d_stream in reply:
        for element in d_stream[1]:
            print(  f"got element {element[0]}"
                  + f"from stream {d_stream[0]}" )
            if run is not None:
                run( d_stream[0], group, element[0] )
# read some messages on group1 with consumer 'c'
d = r.xreadgroup( groupname=group1, consumername='c', block=10,
                  count=2, streams={stream_key:'>'})
print_xreadgroup_reply( d )
got element b'1710790167982-0'from stream b'skey'
got element b'1710790167983-0'from stream b'skey'
A 2nd consumer for the same stream group will get not delivered messages.

# read some messages on group1 with consumer 'c'
d = r.xreadgroup( groupname=group1, consumername='c2', block=10,
                  count=2, streams={stream_key:'>'})
print_xreadgroup_reply( d )
got element b'1710790167983-1'from stream b'skey'
got element b'1710790167983-2'from stream b'skey'
But a 2nd stream group can read the already delivered messages again.

Note that the 2nd stream group include also the 2nd stream. That can be identified in the reply (1st element of the reply list).

d2 = r.xreadgroup( groupname=group2, consumername='c', block=10,
                   count=2, streams={stream_key:'>',stream2_key:'>'})
print_xreadgroup_reply( d2 )
got element b'1710790167982-0'from stream b'skey'
got element b'1710790167983-0'from stream b'skey'
got element b'1710790173142-0'from stream b's2key'
got element b'1710790173143-0'from stream b's2key'
To check for pending messages (delivered messages without acknowledgment) we can use the xpending.

# check pending status (read messages without a ack)
def print_pending_info( key_group ):
    for s,k in key_group:
        pr = r.xpending( name=s, groupname=k )
        print( f"{pr.get('pending')} pending messages on '{s}' for group '{k}'" )

print_pending_info( ((stream_key,group1),(stream_key,group2),(stream2_key,group2)) )
4 pending messages on 'skey' for group 'grp1'
2 pending messages on 'skey' for group 'grp2'
2 pending messages on 's2key' for group 'grp2'
ack
Acknowledge some messages with xack.

# do acknowledges for group1
toack = lambda k,g,e: r.xack( k,g, e )
print_xreadgroup_reply( d, group=group1, run=toack )
got element b'1710790167983-1'from stream b'skey'
got element b'1710790167983-2'from stream b'skey'
# check pending again
print_pending_info( ((stream_key,group1),(stream_key,group2),(stream2_key,group2)) )
2 pending messages on 'skey' for group 'grp1'
2 pending messages on 'skey' for group 'grp2'
2 pending messages on 's2key' for group 'grp2'
ack all messages on the group1.

d = r.xreadgroup( groupname=group1, consumername='c', block=10,
                      count=100, streams={stream_key:'>'})
print_xreadgroup_reply( d, group=group1, run=toack)
print_pending_info( ((stream_key,group1),) )
got element b'1710790167983-3'from stream b'skey'
got element b'1710790167983-4'from stream b'skey'
got element b'1710790167983-5'from stream b'skey'
got element b'1710790167983-6'from stream b'skey'
got element b'1710790167983-7'from stream b'skey'
got element b'1710790167984-0'from stream b'skey'
got element b'1710790173157-0'from stream b'skey'
got element b'1710790173158-0'from stream b'skey'
got element b'1710790173158-1'from stream b'skey'
got element b'1710790173158-2'from stream b'skey'
got element b'1710790173158-3'from stream b'skey'
got element b'1710790173158-4'from stream b'skey'
got element b'1710790173158-5'from stream b'skey'
got element b'1710790173159-0'from stream b'skey'
got element b'1710790173159-1'from stream b'skey'
got element b'1710790173159-2'from stream b'skey'
2 pending messages on 'skey' for group 'grp1'
But stream length will be the same after the xack of all messages on the group1.

r.xlen(stream_key)
20
delete all
To remove the messages with need to remove them explicitly with xdel.

s1 = r.xread( streams={stream_key:0} )
for streams in s1:
    stream_name, messages = streams
    # del all ids from the message list
    [ r.xdel( stream_name, i[0] ) for i in messages ]
stream length

r.xlen(stream_key)
0
But with the xdel the 2nd group can read any not processed message from the skey.

d2 = r.xreadgroup( groupname=group2, consumername='c', block=10,
                   count=2, streams={stream_key:'>',stream2_key:'>'})
print_xreadgroup_reply( d2 )
got element b'1657571042113-1'from stream b's2key'
got element b'1657571042114-0'from stream b's2key'
