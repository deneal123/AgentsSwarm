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
Sample table
Implementing a query to execute SQL expressions in SQLAlchemy
SQLAlchemy provides a function called text(). We can write any conventional SQL query inside the text function enclosed by "". Now, passing this SQL query to execute function will convert this query to SQLAlchemy compatible format and returns the result.

from sqlalchemy import text
text("YOUR SQL QUERY")
Pass the SQL query to the execute() function and get all the results using fetchall() function. Use a for loop to iterate through the results.

Example 1:  Executing basic query
The SQLAlchemy query shown in the below code selects all rows where the book price is greater than Rs. 100.


from sqlalchemy import text

# write the SQL query inside the text() block
sql = text('SELECT * from BOOKS WHERE BOOKS.book_price > 100')
results = engine.execute(sql)

# Fetch all the records
result = engine.execute(sql).fetchall()
  
# View the records
for record in result:
    print("\n", record)
Output:

Click to enlarge
The output of conventional SQL expression
Example 2: Executing insert query
The below SQL expression will insert additional records in the created table in a conventional SQL way.


# define a tuple of dictionary of values to be inserted
data = ( { "book_id": 6, "book_price": 400, 
          "genre": "fiction",
          "book_name": "yoga is science" },
         { "book_id": 7, "book_price": 800, 
          "genre": "non-fiction",
          "book_name": "alchemy tutorials" },
)

# write the insert statement
statement = text("""INSERT INTO BOOKS\
(book_id, book_price, genre, book_name) \
VALUES(:book_id, :book_price, :genre, :book_name)""")

# insert the data one after other using
# execute statement by unpacking dictionary  elements
for line in data:
    engine.execute(statement, **line)

# write the SQL query to check
# whether the records are inserted
sql = text("SELECT * FROM BOOKS ")

results = engine.execute(sql)

# View the records
for record in results:
    print("\n", record)
Output:

Click to enlarge
The output of the insert query
Example 3:  Executing update query
Let us see another example related to update query.


Tablename.update().where(Tablename.c.column_name == 'value').values(column_name = 'value')


Get the books table from the Metadata object initialized while connecting to the database. Pass the delete query to the execute() function and get all the results using fetchall() function. Use a for loop to iterate through the results.

The SQLAlchemy query shown in the below code updates the genre "non-fiction" as "sci-fi" this will effectively update multiple rows at one go. Then, we can write a conventional SQL query and use fetchall() to print the results to check whether the table is updated properly.


# Get the `books` table from the Metadata object
BOOKS = meta.tables['books']

# update
stmt = BOOKS.update().where(BOOKS.c.genre == 'non-fiction'
                           ).values(genre='sci-fi')
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
The result of an update query
Example 4:  Executing delete query
Deleting table elements have a slightly different procedure than that of a conventional SQL query which is  shown below

from sqlalchemy import delete
Tablename.delete().where(Tablename.c.column_name == value)
Get the books table from the Metadata object initialized while connecting to the database. Pass the delete query to the execute() function and get all the results using fetchall() function. Use a for loop to iterate through the results.

The SQLAlchemy query shown in the below code deletes the "fiction" genre this will effectively delete multiple rows at one go. Then, we can write a conventional SQL query and use fetchall() to print the results to check whether the table is updated properly.


# Get the `books` table from the Metadata object
BOOKS = meta.tables['books']

# delete
dele = BOOKS.delete().where(BOOKS.c.genre == "fiction")

engine.execute(dele)

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