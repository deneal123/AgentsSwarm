SQLAlchemy Core - SQL Expressions
Last Updated : 28 Feb, 2022
In this article, we are going to see how to write SQL Expressions using SQLAlchmey  CORE using text() in SQLAlchemy against a PostgreSQL database in Python.

Creating table for demonstration
Import necessary functions from the SQLAlchemy package. Establish connection with the PostgreSQL database using create_engine() function as shown below. Create a table called books with columns book_id and book_price. Insert record into the tables using insert() and values() function as shown.


# import necessary packages
from sqlalchemy.engine import result
from sqlalchemy import create_engine, MetaData,\
Table, Column, Numeric, Integer, VARCHAR
from sqlalchemy import text

# establish connections
engine = create_engine(
    "dialect+driver://username:password@host:port/database_name")

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