SQLAlchemy - Label
Last Updated : 23 Jul, 2025
SQLAlchemy is a Python library used for working with relational databases. It provides an intuitive way to interact with databases and allows us to write database-independent code. In this article, we'll explore one of the powerful features of SQLAlchemy called label(), which is used to add labels to queries and retrieve data in a more convenient way.

What is a Label in SQLAlchemy?
A label in SQLAlchemy is a means to give a result column in a query a name. When you run a query with labels, the result set will have the specified names for the columns rather than the standard column names. Any expression in a SELECT statement, such as columns, functions, and subqueries, can be given a label. In SQLAlchemy, labels are a potent tool for improving the readability of our queries and the practicality of data retrieval. Labels let us give columns in our query names, apply labels to functions, and aggregate our results in more useful ways. Labels help us write more understandable, maintainable code and facilitate database operationsWe will see how we can use label() feature of SQLAlchemy with the help of Python.

Database Table Used

For the purpose of this article, we'll be using a simple database called library.db. It has a table called students containing columns id, name, age, and department. 

SQLAlchemy -Label
DB Table
Displaying Records with Labels
This is an example query using SQLAlchemy to select the "name" column in uppercase and the "age" column for rows where the age is greater than 18, using the select function and the label and func methods from SQLAlchemy.


# Import the necessary SQLAlchemy components
from sqlalchemy import *

# Create a connection to a SQLite database using a SQLAlchemy engine
engine = create_engine('sqlite:///library.db')
connection = engine.connect()

# Define a metadata object and a table object for the "student" table
metadata = MetaData()
table = Table('student', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('age', Integer),
    Column('dept', String),
)

# Create the "student" table in the database
metadata.create_all(engine)

# Insert some sample data into the "student" table
q = text('''
INSERT INTO student(id, name, age, dept) 
    VALUES
    (1, 'Mitul Rao', 20, "Comp"), 
    (2, 'Lochan Patel', 17, "Comp"), 
    (3, 'Inderjeet Ahmad', 17, "Mech"), 
    (4, 'Punita Gadhavi', 25, "Civil"), 
    (5, 'Sarvesh Mishra', 30, "Comp")
''')
connection.execute(q)

# Select all rows from the "student" table and display the results
print('\nDisplaying the table: \n')
q = text("SELECT * FROM student")
result = connection.execute(q)

for row in result.fetchall():
    print(row)

# Define a query to select the "name" column in uppercase and 
# the "age" column for rows where age > 18
query = select(
    label('name_uppercase', func.upper(table.c.name)),
    table.c.age
).where(table.c.age > 18)

# Execute the query and print the results
print('\nDisplaying records labels with age" +
        "greater than 18 age: \n')
with engine.connect() as conn:
    result = connection.execute(query)

    for row in result:
        print(row)

# Close the database connection
connection.close()
Output:

In this example, the records with an age greater than 18 are converted to uppercase under the label "name_uppercase".

SQLAlchemy -Label
Label Output
Using Functions with Labels
Labels can also be used with functions to make the result set more readable. For example, suppose we want to retrieve the number of students according to their department. We can use the label() function and the func.count() function to create a more informative result set.


# Define a query to count the number of rows in the "student" table 
# for each unique value of the "dept" column
query = select(
    label('name_uppercase', func.count(table.c.dept)),
    table.c.dept
).group_by(table.c.dept)

# Execute the query and print the results
print('\nDisplaying records labels count department wise: \n')
with engine.connect() as conn:
    result = connection.execute(query)

    for row in result:
        print(row)
Output:

 Functions with Labels - SQLAlchemy