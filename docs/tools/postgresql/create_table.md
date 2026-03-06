SQLAlchemy Core - Creating Table
Last Updated : 28 May, 2024
In this article, we are going to see how to create table in SQLAlchemy using Python.

SQLAlchemy is a large SQL toolkit with lots of different components. The two largest components are SQLAlchemy Core and SQLAlchemy ORM. The major difference between them is SQLAlchemy Core is a schema-centric model that means everything is treated as a part of the database i.e., rows, columns, tables, etc while SQLAlchemy ORM uses an object-centric view which encapsulates the schema with business objects. SQLAlchemy is a more pythonic implementation. In this post, we shall look at the SQLAlchemy core and how to create a table using it.

Installing SQLAlchemy
SQLAlchemy is available via the pip install package.

pip install sqlalchemy
However, if you are using a flask you can make use of its own implementation of SQLAlchemy. It can be installed using -

pip install flask-sqlalchemy
Creating Database
We are going to make use of the sqlite3 database. Follow the below process to create a database that names users:

Step 1: Open the command prompt and point to the directory to which the sqlite.exe file is present.

Step 2: Create a database named users using the command sqlite3 users.db and Check the created database using the command .databases

Click to enlarge
Creating database using sqlite3
Create a table using SQLAlchemy Core
First, let us look at the entire code and then jump to the explanation and the output for the same


import sqlalchemy as db

# Defining the Engine
engine = db.create_engine('sqlite:///users.db', echo=True)

# Create the Metadata Object
metadata_obj = db.MetaData()

# Define the profile table

# database name
profile = db.Table(
    'profile',                                        
    metadata_obj,                                    
    db.Column('email', db.String, primary_key=True),  
    db.Column('name', db.String),                    
    db.Column('contact', db.Integer),                
)

# Create the profile table
metadata_obj.create_all(engine)
Output:

2021-11-08 11:08:36,988 INFO sqlalchemy.engine.base.Engine ()
2021-11-08 11:08:36,997 INFO sqlalchemy.engine.base.Engine COMMIT
Explanation:
First, we import all the requirements from the sqlalchemy library. After that, we create the engine which is used to perform all the operations like creating tables, inserting or modifying values into a table, etc. From the engine, we can create connections on which we can run database queries on. The metadata_obj contains all the information about our database which is why we pass it in when creating the table. The metadata.create_all(engine) binds the metadata to the engine and creates the profile table if it is not existing in the users database.

Click to enlarge
Output Viewed in SQLite3 terminal
In order to view the tables present in the users database, use the command .tables. In the output, when the command is used for the first time we cannot see any output that is because the above code was not run at that time. After running the above code and then using the .tables command, we can see in the sqlite3 terminal that the profile table that we created using the code is present in the users database. The SELECT query is also successfully executed which indicates the table is created. However, there is no output since we did not insert any entry in the table.