Timeseries
redis-py supports RedisTimeSeries which is a time-series-database module for Redis.

This example shows how to handle timeseries data with redis-py.

Health check
import redis

r = redis.Redis(decode_responses=True)
ts = r.ts()

r.ping()
True
Simple example
Create a timeseries
ts.create("ts_key")
True
Add samples to the timeseries
We can either set the timestamp with an UNIX timestamp in milliseconds or use * to set the timestamp based en server’s clock.

ts.add("ts_key", 1657265437756, 1)
ts.add("ts_key", "1657265437757", 2)
ts.add("ts_key", "*", 3)
1657272304448
Get the last sample
ts.get("ts_key")
(1657272304448, 3.0)
Get samples between two timestamps
The minimum and maximum possible timestamps can be expressed with respectfully - and +.

ts.range("ts_key", "-", "+")
[(1657265437756, 1.0), (1657265437757, 2.0), (1657272304448, 3.0)]
ts.range("ts_key", 1657265437756, 1657265437757)
[(1657265437756, 1.0), (1657265437757, 2.0)]
Delete samples between two timestamps
print("Before deletion: ", ts.range("ts_key", "-", "+"))
ts.delete("ts_key", 1657265437756, 1657265437757)
print("After deletion:  ", ts.range("ts_key", "-", "+"))
Before deletion:  [(1657265437756, 1.0), (1657265437757, 2.0), (1657272304448, 3.0)]
After deletion:   [(1657272304448, 3.0)]
Multiple timeseries with labels
ts.create("ts_key1")
ts.create("ts_key2", labels={"label1": 1, "label2": 2})
True
Add samples to multiple timeseries
ts.madd([("ts_key1", "*", 1), ("ts_key2", "*", 2)])
[1657272306147, 1657272306147]
Add samples with labels
ts.add("ts_key2", "*", 2,  labels={"label1": 1, "label2": 2})
ts.add("ts_key2", "*", 2,  labels={"label1": 3, "label2": 4})
1657272306457
Get the last sample matching specific label
Get the last sample that matches “label1=1”, see Redis documentation to see the posible filter values.

ts.mget(["label1=1"])
[{'ts_key2': [{}, 1657272306457, 2.0]}]
Get also the label-value pairs of the sample:

ts.mget(["label1=1"], with_labels=True)
[{'ts_key2': [{'label1': '1', 'label2': '2'}, 1657272306457, 2.0]}]
Retention period
You can specify a retention period when creating timeseries objects or when adding a sample timeseries object. Once the retention period has elapsed, the sample is removed from the timeseries.

retention_time = 1000
ts.create("ts_key_ret", retention_msecs=retention_time)
True
import time
# this will be deleted in 1000 milliseconds
ts.add("ts_key_ret", "*", 1, retention_msecs=retention_time)
print("Base timeseries:                     ", ts.range("ts_key_ret", "-", "+"))
# sleeping for 1000 milliseconds (1 second)
time.sleep(1)
print("Timeseries after 1000 milliseconds:  ", ts.range("ts_key_ret", "-", "+"))
Base timeseries:                      [(1657272307670, 1.0)]
Timeseries after 1000 milliseconds:   [(1657272307670, 1.0)]
The two lists are the same, this is because the oldest values are deleted when a new sample is added.

ts.add("ts_key_ret", "*", 10)
1657272308849
ts.range("ts_key_ret", "-", "+")
[(1657272308849, 10.0)]
Here the first sample has been deleted.

Specify duplicate policies
By default, the policy for duplicates timestamp keys is set to “BLOCK”, we cannot create two samples with the same timestamp:

ts.add("ts_key", 123456789, 1)
try:
    ts.add("ts_key", 123456789, 2)
except Exception as err:
    print(err)
TSDB: Error at upsert, update is not supported when DUPLICATE_POLICY is set to BLOCK mode
You can change this default behaviour using duplicate_policy parameter, for instance:

# using policy "LAST", we keep the last added sample
ts.add("ts_key", 123456789, 2, duplicate_policy="LAST")
ts.range("ts_key", "-", "+")
[(123456789, 2.0), (1657272304448, 3.0)]
For more informations about duplicate policies, see Redis documentation.

Using Redis TSDB to keep track of a value
ts.add("ts_key_incr", "*", 0)
1657272310241
Increment the value:

for _ in range(10):
    ts.incrby("ts_key_incr", 1)
    # sleeping a bit so the timestamp are not duplicates
    time.sleep(0.01)
ts.range("ts_key_incr", "-", "+")
[(1657272310241, 0.0),
 (1657272310533, 1.0),
 (1657272310545, 2.0),
 (1657272310556, 3.0),
 (1657272310567, 4.0),
 (1657272310578, 5.0),
 (1657272310589, 6.0),
 (1657272310600, 7.0),
 (1657272310611, 8.0),
 (1657272310622, 9.0),
 (1657272310632, 10.0)]
How to execute multi-key commands on Open Source Redis Cluster
import redis

r = redis.RedisCluster(host="localhost", port=46379)

# This command should be executed on all cluster nodes after creation and any re-sharding
# Please note that this command is internal and will be deprecated in the future
r.execute_command("timeseries.REFRESHCLUSTER", target_nodes="primaries")

# Now multi-key commands can be executed
ts = r.ts()
ts.add("ts_key1", "*", 2,  labels={"label1": 1, "label2": 2})
ts.add("ts_key2", "*", 10,  labels={"label1": 1, "label2": 2})
ts.mget(["label1=1"])
[{'ts_key1': [{}, 1670927124746, 2.0]}, {'ts_key2': [{}, 1670927124748, 10.0]}]