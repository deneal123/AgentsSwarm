Column and Data Types in SQLAlchemy
Last Updated : 28 Apr, 2025
SQLAlchemy is an open-source library for the Python programming language that provides a set of tools for working with databases. It allows developers to interact with databases in a more Pythonic way, making it easier to write code that is both efficient and readable.

Column Types
A column type in SQLAlchemy is an object that defines the kind of data that can be kept in a database column. For working with various sorts of data, SQLAlchemy offers a large variety of column types. The following are a few of the most popular column types:

Integer: Integer values are stored in columns of the Integer type. It is commonly utilized to store numerical identifiers like user IDs and product IDs.
String: Text data is stored in columns with the String type. Names, addresses, and other sorts of textual data are commonly stored in it.
Boolean: Boolean values are stored in the Boolean column type (i.e., True or False). Usually, flags or other binary data are stored there.
Date and Time: To store date and time values, use the Date and Time column types. They are commonly utilized to store timestamps and other time-related information.
Float and Decimal: The column types Float and Decimal are used to hold floating-point numbers. They are commonly utilized for storing monetary amounts or other precise numeric data.
Binary: Binary data is stored in the Binary column type. It is often used to store binary data, such as images.
Data Types
SQLAlchemy offers a large variety of data types in addition to column types for working with various forms of data. Although data types and column types are comparable, data types are more general and can be used to express data across several columns. Some of the most common data types include:

String: Text data is represented by the data type String. It's comparable to the String column type and can express text data in numerous columns.
Integer: Integer data types are used to represent integer values. Although it is comparable to the Integer column type, it allows for the representation of integer data across many columns.
Boolean: Boolean values are represented by the Boolean data type. Although it can be used to represent boolean values over many columns, it is comparable to the Boolean column type.
Date and Time: To represent date and time values, use the Date and Time data types. Although they are comparable to the Date and Time column types, they allow for the representation of date and time information across many columns.
Float and Decimal: The data types Float and Decimal are used to represent floating-point numbers. The only difference between them and the Float and Decimal column types is that they can be used to represent floating-point data over several columns.
Creating Tables with Column and Data Types
    Column('id', Integer),
    Column('name', String),
      Column('start_time', DateTime),
     Column('completed', Boolean),
     Column('price', Float),
    Column('discount', Decimal(10, 2)),
    Column('image', LargeBinary),
Example 1:


from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

engine = create_engine('sqlite:///example.db')
metadata = MetaData()

# Define a table with column and data types
users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('age', Integer),
)

# Create the table in the database
metadata.create_all(engine)

# Insert some data into the table
conn = engine.connect()
conn.execute(users.insert().values(name='Alice', age=25))
conn.execute(users.insert().values(name='Bob', age=30))

# Select all users from the table
result = conn.execute(users.select())

# Print the results
for row in result:
    print(row)
Output:

(1, 'Alice', 25)
(2, 'Bob', 30)
Example 2:


from sqlalchemy import create_engine, Table, Column, Integer, String, DateTime, MetaData

engine = create_engine('sqlite:///example.db')
metadata = MetaData()

# Define a table with column and data types
articles = Table(
    'articles', metadata,
    Column('id', Integer, primary_key=True),
    Column('title', String),
    Column('content', String),
    Column('published_at', DateTime),
)

# Create the table in the database
metadata.create_all(engine)

# Insert some data into the table
conn = engine.connect()
conn.execute(articles.insert().values(
    title='Intro to SQLAlchemy',
    content='In this article, we will learn how to use SQLAlchemy to interact with databases.',
    published_at='2022-02-28 12:00:00'
))

# Select all articles from the table
result = conn.execute(articles.select())

# Print the results
for row in result:
    print(row)
Output:

(
1, 'Intro to SQLAlchemy',
 'In this article,
 we will learn how to use SQLAlchemy to interact with databases.', 
'2022-02-28 12:00:00'
)
Example 3:


from sqlalchemy import create_engine, Column, Boolean, Float, Decimal, LargeBinary

engine = create_engine('sqlite:///example.db')
metadata = Base.metadata

product_table = Table('products', metadata,
    Column('id', Integer, primary_key=True),
    Column('completed', Boolean),
    Column('price', Float),
    Column('discount', Decimal(10, 2)),
    Column('image', LargeBinary),
)

metadata.create_all(engine)

from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()

new_product = product_table.insert().values(completed=True, price=9.99, discount=1.50, image=b'\x00\x01\x02')
session.execute(new_product)
session.commit()

products = session.query(product_table).filter(product_table.c.price < 10).all()

for product in products:
    print(product)
Output:

(1, True, 9.99, Decimal('1.50'), b'\x00\x01\x02')