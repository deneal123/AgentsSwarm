Indexing / querying JSON documents
Adding a JSON document to an index
import redis
from redis.commands.json.path import Path
import redis.commands.search.aggregation as aggregations
import redis.commands.search.reducers as reducers
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import NumericFilter, Query


r = redis.Redis(host='localhost', port=6379)
user1 = {
    "user":{
        "name": "Paul John",
        "email": "paul.john@example.com",
        "age": 42,
        "city": "London"
    }
}
user2 = {
    "user":{
        "name": "Eden Zamir",
        "email": "eden.zamir@example.com",
        "age": 29,
        "city": "Tel Aviv"
    }
}
user3 = {
    "user":{
        "name": "Paul Zamir",
        "email": "paul.zamir@example.com",
        "age": 35,
        "city": "Tel Aviv"
    }
}

user4 = {
    "user":{
        "name": "Sarah Zamir",
        "email": "sarah.zamir@example.com",
        "age": 30,
        "city": "Paris"
    }
}
r.json().set("user:1", Path.root_path(), user1)
r.json().set("user:2", Path.root_path(), user2)
r.json().set("user:3", Path.root_path(), user3)
r.json().set("user:4", Path.root_path(), user4)

schema = (TextField("$.user.name", as_name="name"),TagField("$.user.city", as_name="city"), NumericField("$.user.age", as_name="age"))
r.ft().create_index(schema, definition=IndexDefinition(prefix=["user:"], index_type=IndexType.JSON))
b'OK'
Searching
Simple search
r.ft().search("Paul")
Result{2 total, docs: [Document {'id': 'user:1', 'payload': None, 'json': '{"user":{"name":"Paul John","email":"paul.john@example.com","age":42,"city":"London"}}'}, Document {'id': 'user:3', 'payload': None, 'json': '{"user":{"name":"Paul Zamir","email":"paul.zamir@example.com","age":35,"city":"Tel Aviv"}}'}]}
Filtering search results
q1 = Query("Paul").add_filter(NumericFilter("age", 30, 40))
r.ft().search(q1)
Result{1 total, docs: [Document {'id': 'user:3', 'payload': None, 'json': '{"user":{"name":"Paul Zamir","email":"paul.zamir@example.com","age":35,"city":"Tel Aviv"}}'}]}
Paginating and Ordering search Results
# Search for all users, returning 2 users at a time and sorting by age in descending order
offset = 0
num = 2
q = Query("*").paging(offset, num).sort_by("age", asc=False) # pass asc=True to sort in ascending order
r.ft().search(q)
Result{4 total, docs: [Document {'id': 'user:1', 'payload': None, 'age': '42', 'json': '{"user":{"name":"Paul John","email":"paul.john@example.com","age":42,"city":"London"}}'}, Document {'id': 'user:3', 'payload': None, 'age': '35', 'json': '{"user":{"name":"Paul Zamir","email":"paul.zamir@example.com","age":35,"city":"Tel Aviv"}}'}]}
Counting the total number of Items
q = Query("*").paging(0, 0)
r.ft().search(q).total
4
Projecting using JSON Path expressions
r.ft().search(Query("Paul").return_field("$.user.city", as_field="city")).docs
[Document {'id': 'user:1', 'payload': None, 'city': 'London'},
 Document {'id': 'user:3', 'payload': None, 'city': 'Tel Aviv'}]
Aggregation
req = aggregations.AggregateRequest("Paul").sort_by("@age")
r.ft().aggregate(req).rows
[[b'age', b'35'], [b'age', b'42']]
Count the total number of Items
# The group_by expects a string or list of strings to group the results before applying the aggregation function to
# each group. Passing an empty list here acts as `GROUPBY 0` which applies the aggregation function to the whole results
req = aggregations.AggregateRequest("*").group_by([], reducers.count().alias("total"))
r.ft().aggregate(req).rows
[[b'total', b'4']]