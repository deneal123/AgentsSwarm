SQLAlchemy ORM - Adding Objects
Last Updated : 18 Mar, 2022
In this article, we will discuss how to add objects in the SQLAlchemy ORM.

The SQLAlchemy Object Relational Mapper presents a method of associating user-defined Python classes with database tables and instances of those classes (objects) with rows in their corresponding tables. For this article, we're going to use the Postgres database. You can also use an in-memory-only SQL database.

Make sure you've properly installed sqlalchemy if not then install it with:

pip install sqlachemy
For example, You've designed an API that stores and fetches the posts created by the user in the database, somewhat like GFG, Instagram, etc. This is the class that is mapped to our database table "posts" 


from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

# Declare Mapping
Base = declarative_base()

# This is the  class which is mapped to "posts" 
# table to our database
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    published = Column(Boolean, server_default='true', nullable=False)
Stepwise Implementation
Step 1: Database related configuration

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Syntax of database url = "<database_vendor_name>:
# //<username>:<password>@ip-address/hostname/
# <database_name>"
DB_URL = "postgresql://anurag:anurag@localhost/gfg"

engine = create_engine(DB_URL)

local_session = sessionmaker(autoflush=False, 
                             autocommit=False, bind=engine)

# With this we get a session to do whatever
# we want to do
db = local_session()
Step 2: To add a new object (post)
Here, we are creating an object, and then with the use of the db.add() function, we have added the created object to the database.


# New post created by a user, assumes 
# you get this from the frontend
post = Post(title="GFG Article",
            content="How to add SQL Alchemy objects", 
            published=True)

db.add(post)
Click to enlarge
As you can see above post is not saved to the database till you committed it like,


# To store the object to the database, 
# otherwise the transaction remains pending
db.commit()

# After performing transaction, we should
# always close our connection to the database
# It's a good practice and we must follow it
db.close()

print("Successfully added a new post")
Note: Every time you made changes make sure that you've committed the transaction, otherwise the transaction is pending. 

After committing the transaction you've successfully saved a new object to your database, you can query the database regarding the changes

Step 3: Querying the database
Under this, we are verifying if the object is successfully added or not. If it is added then the database will show the same object else it won't be present in the database.

SELECT * FROM posts;
And you get all your posts saved in your local database.

Click to enlarge
Complete Script to add new objects to the database:


from sqlalchemy import Column, Integer, Boolean, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Declare Mapping
Base = declarative_base()


# This is the  class which is mapped to "posts" 
# table to our database
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    published = Column(Boolean, server_default='true', nullable=False)


# Syntax of database url = "<database_vendor_name>://
# <username>:<password>@ip-address/hostname/<database_name>"
DB_URL = "postgresql://anurag:anurag@localhost/gfg"

engine = create_engine(DB_URL)

local_session = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# With this we get a session to do whatever we 
# want to do
db = local_session()

# New post created by a user, assumes you get this
# from the frontend
post = Post(title="GFG Article",
            content="How to add SQL Alchemy objects", published=True)

db.add(post)
db.commit()

# After performing transaction, we should always close
# our connection to the database
db.close()

print("Successfully added a new post")
Output:

Click to enlarge
