Pipeline examples
This example show quickly how to use pipelines in redis-py.

Checking that Redis is running
import redis

r = redis.Redis(decode_responses=True)
r.ping()
True
Simple example
Creating a pipeline instance
pipe = r.pipeline()
Adding commands to the pipeline
pipe.set("a", "a value")
pipe.set("b", "b value")

pipe.get("a")
Pipeline<ConnectionPool<Connection<host=localhost,port=6379,db=0>>>
Executing the pipeline
pipe.execute()
[True, True, 'a value']
The responses of the three commands are stored in a list. In the above example, the two first boolean indicates that the set commands were successful and the last element of the list is the result of the get("a") comand.

Chained call
The same result as above can be obtained in one line of code by chaining the opperations.

pipe = r.pipeline()
pipe.set("a", "a value").set("b", "b value").get("a").execute()
[True, True, 'a value']
Here’s a slightly more advanced example for chaining complex operations using the builder pattern.

from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    email: str
    username: Optional[str] = None

@dataclass
class Post:
    title: str
    body: str
    author: Optional[str] = None

class RedisRepository:
    def __init__(self):
        self.pipeline = r.pipeline()

    def add_user(self, user: User):
        if not user.username:
            user.username = user.email.split("@")[0]
        self.pipeline.hset(f"user:{user.username}", mapping={"username": user.username, "email": user.email})
        return self

    def add_post(self, post: Post):
        self.pipeline.hset(f"post:#{post.title}#", mapping={"title": post.title, "body": post.body, "author": post.author})
        if post.author:
            self.pipeline.sadd(f"user:{post.author}:posts", f"post:#{post.title}#")
        return self

    def add_follow(self, follower: str, following: str):
        self.pipeline.sadd(f"user:{follower}:following", following)
        self.pipeline.sadd(f"user:{following}:followers", follower)
        return self

    def execute(self):
        return self.pipeline.execute()

pipe = RedisRepository()
results = (pipe
    .add_user(User(email="alice@example.com"))
    .add_user(User(email="bob@example.com"))
    .add_follow("alice", "bob")
    .add_post(Post(title="Hello World", body="I'm using Redis!", author="alice"))
    .execute()
)
Performance comparison
Using pipelines can improve performance, for more informations, see Redis documentation about pipelining. Here is a simple comparison test of performance between basic and pipelined commands (we simply increment a value and measure the time taken by both method).

from datetime import datetime

incr_value = 100000
Without pipeline
r.set("incr_key", "0")

start = datetime.now()

for _ in range(incr_value):
    r.incr("incr_key")
res_without_pipeline = r.get("incr_key")

time_without_pipeline = (datetime.now() - start).total_seconds()
print("Without pipeline")
print("================")
print("Time taken: ", time_without_pipeline)
print("Increment value: ", res_without_pipeline)
Without pipeline
================
Time taken:  21.759733
Increment value:  100000
With pipeline
r.set("incr_key", "0")

start = datetime.now()

pipe = r.pipeline()
for _ in range(incr_value):
    pipe.incr("incr_key")
pipe.get("incr_key")
res_with_pipeline = pipe.execute()[-1]

time_with_pipeline = (datetime.now() - start).total_seconds()
print("With pipeline")
print("=============")
print("Time taken: ", time_with_pipeline)
print("Increment value: ", res_with_pipeline)
With pipeline
=============
Time taken:  2.357863
Increment value:  100000
Using pipelines provides the same result in much less time.