SQLAlchemy ORM - Declaring Mapping
Last Updated : 18 Mar, 2022
In this article, we will see how to declare mapping using SQLAlchemy in Python.

You will need a database (MySQL, PostgreSQL, SQLite, etc) to work with. Since we are going to use MySQL in this post, we will also install a SQL connector for MySQL in Python. However, none of the code implementations changes with change in the database except for the SQL connectors.

pip install pymysql
We will use the sample sakila database from MySQL. In this article, we will cover 2 examples. In both examples, we will declare mapping for the actor table within the sakila database. If you do not have the sakila database and want to follow along with this article without installing it then use the SQL script present in the link mentioned below to create the required schema and actor table along with the records.

Database Used: Sakila Actor Table Script

The SQL query which we are looking at in the below two examples is -

SELECT COUNT(*) FROM sakila.`actor`;
SQLAlchemy Core uses an object-centric view that encapsulates the schema with business objects. It is a more pythonic implementation where the tables are mapped using object-oriented classes in python. In SQLAlchemy, there are 2 different ways in which we can declare mapper configurations, namely, Declarative and Classical/Imperative. The “Classical” or "Imperative" style is SQLAlchemy’s original mapping API, whereas “Declarative” is the richer and more succinct system that builds on top of “Classical”.  Let us see how we can declare mapping using both these ways.

Declarative Mapping:
For the below example, we have used declarative mapping. In this, we create an Actor class that inherits from a `declarative_base()` method. We then provide the table name and schema name as mentioned in the example. Please note that the schema name might not be required in MySQL databases (since database and schema name are eventually the same in MySQL) but can come as a handy setting for the PostgreSQL database where schema and databases are distinct. We have mapped the `actor` table from the sakila database using the `Actor` class. In order to test whether our mapping is working or not, we create a sqlalchemy engine connection, and using this connection we query the database using SQLAlchemy's ORM method. In the provided example, we are fetching the count of the records in the `actor` table. We can also look at the data type of the `Actor` class; it represents SQLAlchemy's ORM object.


from sqlalchemy.orm import sessionmaker
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

# MAPPING CLASS ACTOR USING DECLARATIVE MAPPING


class Actor(Base):

    __table_args__ = {'schema': 'sakila'}
    __tablename__ = 'actor'

    actor_id = db.Column(db.SmallInteger, autoincrement=True, primary_key=True)
    first_name = db.Column(db.String(45), nullable=False)
    first_name = db.Column(db.String(45), nullable=False)
    last_update = db.Column(db.TIMESTAMP, nullable=False, server_default=db.text(
        'CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))


# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql://root:password@localhost/sakila")

# CREATE A SESSION OBJECT TO INITIATE QUERY IN DATABASE
Session = sessionmaker(bind=engine)
session = Session()

# SELECT COUNT(*) FROM Actor
result = session.query(Actor).count()

print("Count of Records in Actor Table:", result)
print("Type of Actor Class:", type(Actor))
Output:

Count of Records in Actor Table: 200
Type of Actor Class: <class 'sqlalchemy.orm.decl_api.DeclarativeMeta'>
Classical/Imperative Mapping:
The declarative mapping shown in the first example is built on top of the classical or imperative mapping.  The Imperative Mapping uses the SQLAlchemy's Core method to define the databases and then wraps around using SQLAlchemy ORM's `mapper()` method so that the mapping begins ORM registry object, which maintains a set of classes that are mapped (just like the declarative mapping). You can compare both the examples to figure out that once we have created these mapper objects we can use the same ORM syntax to query the database. In this example, we are again fetching the number of records from the `actor` table present in the `sakila` database. It is worth that in this example as well the `Actor` class represents SQLAlchemy's ORM object.


from sqlalchemy.orm import sessionmaker
import sqlalchemy as db
from sqlalchemy.orm import mapper

# CREATE THE METADATA OBJECT REQUIRED TO CREATE THE TABLE
metadata = db.MetaData()

# DEFINE THE ACTOR TABLE USING SQLALCHEMY CORE
actor = db.Table(
    'actor',
    metadata,
    db.Column('actor_id', db.SmallInteger,
              autoincrement=True, primary_key=True),
    db.Column('first_name', db.String(45), nullable=False),
    db.Column('last_name', db.String(45), nullable=False),
    db.Column('last_update', db.TIMESTAMP, nullable=False, server_default=db.text(
        'CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
)

# MAPPING CLASS ACTOR USING CLASSICAL MAPPING


class Actor(object):

    def __init__(self, first_name, last_name) -> None:
        self.first_name = first_name
        self.last_name = last_name


mapper(Actor, actor)

# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql://root:password@localhost/sakila")

# CREATE A SESSION OBJECT TO INITIATE QUERY IN DATABASE
Session = sessionmaker(bind=engine)
session = Session()

# SELECT COUNT(*) FROM Actor
result = session.query(Actor).count()

print("Count of Records in Actor Table:", result)
print("Type of Actor Class:", type(Actor))
Output:

Count of Records in Actor Table: 200
Type of Actor Class: <class 'sqlalchemy.orm.decl_api.DeclarativeMeta'>