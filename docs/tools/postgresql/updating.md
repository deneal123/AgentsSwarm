SQLAlchemy core - Update statement
Last Updated : 31 Jan, 2022
In this article, we are going to see how to use the UPDATE statement in SQLAlchemy against a PostgreSQL database in Python.

Creating table for demonstration
Import necessary functions from the SQLAlchemy package. Establish connection with the PostgreSQL database using create_engine() function as shown below, create a table called books with columns book_id and book_price. Insert record into the tables using insert() and values() function as shown.


# import necessary packages
from sqlalchemy.engine import result
import sqlalchemy
from sqlalchemy import create_engine, MetaData,
Table, Column, Numeric, Integer, VARCHAR, update

# establish connections
engine = create_engine(
    "database+dialect://username:password0@host:port/databasename")

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
Implementing a query to update table elements in SQLAlchemy
Example 1: Query to update table 
Updating table elements have a slightly different procedure than that of a conventional SQL query which is  shown below

from sqlalchemy import update
upd = update(tablename)
val = upd.values({"column_name":"value"})
cond = val.where(tablename.c.column_name == value)
Get the books table from the Metadata object initialized while connecting to the database. Pass the update query to the execute() function and get all the results using fetchall() function. Use a for loop to iterate through the results. 

The SQLAlchemy query shown in the below code updates the book name of row 3 as "2022 future ahead". Then, we can write a conventional SQL query and use fetchall() to print the results to check whether the table is updated properly.


# Get the `books` table from the Metadata object
BOOKS = meta.tables['books']

# update
u = update(BOOKS)
u = u.values({"book_name": "2022 future ahead"})
u = u.where(BOOKS.c.book_id == 3)
engine.execute(u)


# write the SQL query inside the
# text() block to fetch all records
sql = text("SELECT * from BOOKS")

# Fetch all the records
result = engine.execute(sql).fetchall()

# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge
The result of the Update query.
Example 2: Query to update a table based on the value
Let us see another example related to update query. The update query shown below updates the genre fiction as "sci-fi".


Tablename.update().where(Tablename.c.column_name == 'value').values(column_name = 'value')



# Get the `books` table from the Metadata object
BOOKS = meta.tables['books']

# update
stmt = BOOKS.update().where(BOOKS.c.genre == 'non-fiction'
                           ).values(genre = 'sci-fi')
engine.execute(stmt)

# write the SQL query inside the
# text() block to fetch all records
sql = text("SELECT * from BOOKS")

# Fetch all the records
result = engine.execute(sql).fetchall()

# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge
The output of the update query
Example 3: Query to update a table based on the Condition
The below query updates the book_price by adding 50 bucks to books amounting to less than or equal to100. 


# Get the `books` table from the Metadata object
BOOKS = meta.tables['books']

# update
stmt = BOOKS.update().where(BOOKS.c.book_price <= 100
                           ).values(book_price= BOOKS.c.book_price + 50)
engine.execute(stmt)

# write the SQL query inside the
# text() block to fetch all records
sql = text("SELECT * from BOOKS")

# Fetch all the records
result = engine.execute(sql).fetchall()

# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge