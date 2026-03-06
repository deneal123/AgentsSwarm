SQLAlchemy Core - Using Aliases
Last Updated : 31 Jan, 2022
In this article, we are going to see Aliases in SQLAlchemy Core using Python.

Creating table for demonstration
Import necessary functions from the SQLAlchemy package. Establish connection with the PostgreSQL database using create_engine() function as shown below. Create a table called books with columns book_id and book_price. Insert record into the tables using insert() and values() function as shown.


# import necessary packages
import sqlalchemy
from sqlalchemy import create_engine, MetaData,
Table, Column, Numeric, insert, Integer,
VARCHAR, update, text, delete
from sqlalchemy.engine import result

# establish connections
engine = create_engine(
    "database+dialect://username:password@hostname:port/database_name")

# initialize the Metadata Object
meta = MetaData(bind=engine)
MetaData.reflect(meta)

# create a table schema
books = Table(
    'books', meta,
    Column('book_id', Integer, primary_key=True),
    Column('book_price', Numeric),
    Column('genre', VARCHAR),
    Column('book_name', VARCHAR)
)

meta.create_all(engine)
# insert records into the table
statement1 = books.insert().values(book_id=1,
                                   book_price=12.2,
                                   genre='fiction',
                                   book_name='Old age')
statement2 = books.insert().values(book_id=2, 
                                   book_price=13.2,
                                   genre='non-fiction', 
                                   book_name='Saturn rings')
statement3 = books.insert().values(book_id=3, 
                                   book_price=121.6,
                                   genre='fiction',
                                   book_name='Supernova')
statement4 = books.insert().values(book_id=4, 
                                   book_price=100,
                                   genre='non-fiction',
                                   book_name='History of the world')
statement5 = books.insert().values(book_id=5,
                                   book_price=1112.2,
                                   genre='fiction',
                                   book_name='Sun city')

# execute the insert records statement
engine.execute(statement1)
engine.execute(statement2)
engine.execute(statement3)
engine.execute(statement4)
engine.execute(statement5)
Output:

Click to enlarge
Sample table
Implementing alias in SQLAlchemy
SQL alias is a method of giving a temporary name for a table that is more convenient and readable. SQL alias facilitates a simple name to be used in place of a complex table name when it has to be used multiple times in a query. The alias() function in sqlalchemy.sql module represents an SQL alias. Let us now see how to implement alias in practice.

from sqlalchemy.sql import alias
tablename.alias("a")
Get the books table from the Metadata object initialized while connecting to the database. use the alias table name while executing the query and get all the results using fetchall() function. Use a for loop to iterate through the results.

The below query selects the records where book_id > 3 with "b" as an alias name for the BOOKS table.


# Get the `books` table from the Metadata object
from sqlalchemy.sql import alias, select
BOOKS = meta.tables['books']

b = BOOKS.alias("a")
s = select([b]).where(b.c.book_id > 2)

# Fetch all the records
result = engine.execute(s).fetchall()

# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge
The output of the alias function