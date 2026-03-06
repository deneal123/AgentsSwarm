Connecting to SQL Database using SQLAlchemy in Python
Last Updated : 23 Jul, 2025
In this article, we will see how to connect to an SQL database using SQLAlchemy in Python.

To connect to a SQL database using SQLAlchemy we will require the sqlalchemy library installed in our python environment. It can be installed using pip -

!pip install sqlalchemy
The create_engine() method of sqlalchemy library takes in the connection URL and returns a sqlalchemy engine that references both a Dialect and a Pool, which together interpret the DBAPI’s module functions as well as the behavior of the database.


Syntax: sqlalchemy.create_engine(url, **kwargs)


Parameters:


url: str

The connection URL to the database of type "dialect+driver://username:password@host:port/database".


Example 1: For MySQL Database
In this example,  we have successfully created a connection to the MySQL database. Please note that we have created the database named 'GeekForGeeks' in the local instance of mySQL server with the password set as 'password'. The dialect and driver for establishing the connection to MySQL database are MySQL and pymysql respectively.


# IMPORT THE SQALCHEMY LIBRARY's CREATE_ENGINE METHOD
from sqlalchemy import create_engine

# DEFINE THE DATABASE CREDENTIALS
user = 'root'
password = 'password'
host = '127.0.0.1'
port = 3306
database = 'GeeksForGeeks'

# PYTHON FUNCTION TO CONNECT TO THE MYSQL DATABASE AND
# RETURN THE SQLACHEMY ENGINE OBJECT
def get_connection():
    return create_engine(
        url="mysql+pymysql://{0}:{1}@{2}:{3}/{4}".format(
            user, password, host, port, database
        )
    )


if __name__ == '__main__':

    try:
      
        # GET THE CONNECTION OBJECT (ENGINE) FOR THE DATABASE
        engine = get_connection()
        print(
            f"Connection to the {host} for user {user} created successfully.")
    except Exception as ex:
        print("Connection could not be made due to the following error: \n", ex)
Output:

$ Connection to the 127.0.0.1 for user root created successfully.
Example 2: For PostgreSQL Database
In this example, a sqlalchemy engine connection has been established with the PostgreSQL database. Please note that we have used the pre-existing database named 'postgres' that comes within the local instance of postgresql server. The dialect and driver for establishing the connection to MySQL database is postgres.


# IMPORT THE SQALCHEMY LIBRARY's CREATE_ENGINE METHOD
from sqlalchemy import create_engine

# DEFINE THE DATABASE CREDENTIALS
user = 'root'
password = 'password'
host = '127.0.0.1'
port = 5432
database = 'postgres'

# PYTHON FUNCTION TO CONNECT TO THE POSTGRESQL DATABASE AND
# RETURN THE SQLACHEMY ENGINE OBJECT
def get_connection():
    return create_engine(
        url="postgresql://{0}:{1}@{2}:{3}/{4}".format(
            user, password, host, port, database
        )
    )


if __name__ == '__main__':

    try:
        # GET THE CONNECTION OBJECT (ENGINE) FOR THE DATABASE
        engine = get_connection()
        print(
            f"Connection to the {host} for user {user} created successfully.")
    except Exception as ex:
        print("Connection could not be made due to the following error: \n", ex)
Output:

$ Connection to the 127.0.0.1 for user root created successfully.