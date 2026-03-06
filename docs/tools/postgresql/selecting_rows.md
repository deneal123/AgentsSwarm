SQLAlchemy Core - Selecting Rows
Last Updated : 2 Apr, 2025
In this article, we are going to see how to write a query to get all rows based on certain conditions in SQLAlchemy against a PostgreSQL database in python.

Creating table for demonstration:
Import necessary functions from the SQLAlchemy package. Establish connection with the PostgreSQL database using create_engine() function as shown below, create a table called books with columns book_id and book_price. Insert record into the tables using insert() and values() function as shown.


# import necessary packages
import sqlalchemy
from sqlalchemy import create_engine, MetaData, 
Table, Column, Numeric, Integer, VARCHAR
from sqlalchemy.engine import result

# establish connections
engine = create_engine(
    "database+dialect://username:password0@host:port/databasename")

# initialize the Metadata Object
meta = MetaData(bind=engine)
MetaData.reflect(meta)

# create a table schema
books = Table(
    'books', meta,
    Column('bookId', Integer, primary_key=True),
    Column('book_price', Numeric),
    Column('genre', VARCHAR),
    Column('book_name', VARCHAR)
)

meta.create_all(engine)

# insert records into the table
statement1 = books.insert().values(bookId=1, book_price=12.2,
                                   genre='fiction',
                                   book_name='Old age')
statement2 = books.insert().values(bookId=2, book_price=13.2,
                                   genre='non-fiction',
                                   book_name='Saturn rings')
statement3 = books.insert().values(bookId=3, book_price=121.6,
                                   genre='fiction', 
                                   book_name='Supernova')
statement4 = books.insert().values(bookId=4, book_price=100,
                                   genre='non-fiction',
                                   book_name='History of the world')
statement5 = books.insert().values(bookId=5, book_price=1112.2,
                                   genre='fiction', book_name='Sun city')

# execute the insert records statement
engine.execute(statement1)
engine.execute(statement2)
engine.execute(statement3)
engine.execute(statement4)
engine.execute(statement5)
Output:

Click to enlarge
Sample table
Extract complete rows in SQLAlchemy
Selecting rows in a table has a slightly different procedure than that of a conventional SQL query which is  shown below

sqlalchemy.select(Tablename).where(Tablename.c.column_name == condition)

Get the books table from the Metadata object initialized while connecting to the database. Pass the SQL query to the execute() function and get all the results using fetchall() function. Use a for loop to iterate through the results. The SQLAlchemy query shown in the below code selects all rows where the row contains a "fiction" genre.


# Get the books table from the Metadata object
BOOKS = meta.tables['books']

# SQLAlchemy Query to select all rows with 
# fiction genre
query = sqlalchemy.select(BOOKS).where(BOOKS.c.genre == 'fiction')

# Fetch all the records
result = engine.execute(query).fetchall()

# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge