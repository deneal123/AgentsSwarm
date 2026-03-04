Basic set and get operations
Start off by connecting to the redis server
To understand what decode_responses=True does, refer back to this document

import redis

r = redis.Redis(decode_responses=True)
r.ping()
True
The most basic usage of set and get

r.set("full_name", "john doe")
True
r.exists("full_name")
1
r.get("full_name")
'john doe'
We can override the existing value by calling set method for the same key

r.set("full_name", "overridee!")
True
r.get("full_name")
'overridee!'
It is also possible to pass an expiration value to the key by using setex method

r.setex("important_key", 100, "important_value")
True
r.ttl("important_key")
100
A dictionary can be inserted like this

dict_data = {
    "employee_name": "Adam Adams",
    "employee_age": 30,
    "position": "Software Engineer",
}

r.mset(dict_data)
True
To get multiple keys’ values, we can use mget. If a non-existing key is also passed, Redis return None for that key

r.mget("employee_name", "employee_age", "position", "non_existing")
['Adam Adams', '30', 'Software Engineer', None]