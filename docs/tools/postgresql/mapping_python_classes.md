SQLAlchemy - Mapping Python Classes
Last Updated : 23 Jul, 2025
SQLAlchemy is a popular Python library that provides a nice API for interacting with databases. One of its key features is the ability to map Python classes to database tables, allowing you to use Python objects to represent rows in a database table. This is known as an "object-relational mapper" (ORM).

Types of Mappings in Python Classes
In SQLAlchemy, there are several ways to define the relationship between a Python class and a database table. These include:

Declarative Mapping
Classical Mapping
Runtime Introspection of Mappings, Objects
What is Declarative Mapping
This is the most common way of defining a mapping in SQLAlchemy. It involves defining a Python class and using special SQLAlchemy functions and decorators to define the columns, relationships, and other metadata of the table. This approach is simple and easy to use, and it allows you to define your mappings in a clear and concise way.

To use Declarative Mapping in SQLAlchemy, you need to do the following steps to consider:

Create a base class for declarative mapping using the declarative_base function. This base class will be used as a base for all of your mapping classes.
Define a mapping class for each table in your database. The mapping class should subclass the base class and define the columns of the table using Column objects. You can also use the __tablename__ attribute to specify the name of the table.
Use the create_all method of the Base.metadata object to create the tables in the database.
Use the sessionmaker function to create a session for querying the database.
Use the query method of the session to query the database and retrieve instances of the mapping classes.
Use the add method of the session to add new instances of the mapping classes to the database.
Use the commit method of the session to save your changes to the database.
Example 
Here is an example of declarative mapping in SQLAlchemy, using an in-memory SQLite database. Here, we define a User class that represents a row in the user's table. We use the __tablename__ attribute to specify the name of the table, and the Column class to define the columns of the table. Then, we create the user's table in the database using the create_all method of Base.metadata.

Next, we create a Session object to manage the connection to the database and use it to add a new User object to the database and commit the changes. Finally, we use the session.query method to retrieve all rows from the user's table and print the result.


from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# create an in-memory SQLite database
engine = create_engine('sqlite:///:memory:', echo=True)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    password = Column(String)

    def __repr__(self):
        return f"<User(name='{self.name}', 
      fullname='{self.fullname}', password='{self.password}'>"

# create the users table
Base.metadata.create_all(engine)

# create a session to manage the connection to the database
Session = sessionmaker(bind=engine)
session = Session()

# add a new user to the database
user = User(name='john', fullname='John Doe', password='password')
session.add(user)
session.commit()

# query the users table
users = session.query(User).all()
print(users)
# Output: [<User(name='john', fullname='John Doe', password='password')>]
Output:

[<User(name='john', fullname='John Doe', password='password')>]
What is Classical Mapping
This is an older way of defining mappings in SQLAlchemy, and it involves creating a Mapper object and using it to map a Python class to a database table. This approach is more flexible than declarative mapping, but it can be more verbose and harder to use.

To use Classical Mapping in SQLAlchemy, you need to do the following steps to consider:

Import the Table, mapper, and relationship functions from SQLAlchemy.
Define the structure of the table using a Table object. The Table object should have columns defined using Column objects.
Create a Python class to represent the table. The class should have attributes that correspond to the columns of the table.
Use the mapper function to map the Python class to the Table object.
Use the relationship function to define relationships between tables.
Example
Here is an example of classical mapping in SQLAlchemy, using an in-memory SQLite database. Here, we define a User class that represents a row in the user's table. We use the Table class to define the user's table, specifying the columns and their types. Then, we create a mapper using the mapper function, which maps the User class to the user's table.

Next, we create the users' table in the database using the create_all method of metadata. Then, we create a Session object to manage the connection to the database and use it to add a new User object to the database and commit the changes. Finally, we use the session.query method to retrieve all rows from the users' table and print the result.


from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String
from sqlalchemy.orm import mapper, sessionmaker

# create an in-memory SQLite database
engine = create_engine('sqlite:///:memory:', echo=True)

metadata = MetaData()
users_table = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('fullname', String),
    Column('password', String)
)

class User:
    def __init__(self, name, fullname, password):
        self.name = name
        self.fullname = fullname
        self.password = password

    def __repr__(self):
        return f"<User(name='{self.name}', 
      fullname='{self.fullname}', password='{self.password}')>"

# create a mapper to map the User class to the users table
mapper(User, users_table)

# create the users table
metadata.create_all(engine)

# create a session to manage the connection to the database
Session = sessionmaker(bind=engine)
session = Session()

# add a new user to the database
user = User(name='john', fullname='John Doe', password='password')
session.add(user)
session.commit()

# query the users table
users = session.query(User).all()
print(users)
# Output: [<User(name='john', fullname='John Doe', password='password')>]
Output:

[<User(name='john', fullname='John Doe', password='password')>]
Runtime Introspection of Mappings, Objects
This involves using the SQLAlchemy reflection API to introspect an existing database and create mappings for the tables and columns that it finds. This is a useful way to quickly create mappings for an existing database, but it does not give you as much control over the mappings as the other approaches.

Example
Import the necessary modules from SQLAlchemy, including create_engine, Column, Integer, String, MetaData, Table, declarative_base, sessionmaker, and inspect. Create an engine and connect it to the database using the create_engine function. Reflect the existing tables in the database using the reflect method of the MetaData object. Create a base class for declarative mapping using the declarative_base function. Define the structure of the table using a mapping class that subclasses the base class. The mapping class should define the columns of the table using Column objects. Create the table in the database using the create_all method of the Base.metadata object. Insert some data into the table using the insert method of the __table__ attribute of the mapping class. Create a session to use for querying the database using the sessionmaker function. Query the database and get an instance of the mapping class using the query method of the session. Use the inspect function to introspect the instance. Print the column names of the instance using the attrs attribute of the inspector object.


from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

# Create an engine and connect to the database
engine = create_engine('sqlite:///mydatabase.db')

# Reflect the existing tables in the database
metadata = MetaData()
metadata.reflect(bind=engine)

# Create a base class for declarative mapping
Base = declarative_base()

# Define the structure of the table using a mapping class
class MyTable(Base):
    __tablename__ = 'my_table'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(Integer)

# Create the table in the database
Base.metadata.create_all(engine)

# Insert some data into the table
engine.execute(MyTable.__table__.insert(), [
    {'name': 'foo', 'value': 1},
    {'name': 'bar', 'value': 2},
    {'name': 'baz', 'value': 3},
])

# Create a session to use for querying
Session = sessionmaker(bind=engine)
session = Session()

# Query the database and get an instance of the mapped class
instance = session.query(MyTable).first()

# Use the inspect function to introspect the instance
inspector = inspect(instance)

# Print the column names 
print("Columns:")
for column in inspector.attrs:
    print(f"{column.key}")
Output:

Columns:
id
name
value