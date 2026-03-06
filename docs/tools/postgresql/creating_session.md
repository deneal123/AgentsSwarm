SQLAlchemy ORM - Creating Session
Last Updated : 4 Jan, 2022
In this article, we will see how to create a session for SQLAlchemy ORM queries.

Before we begin, let us install the required dependencies using pip:

pip install sqlalchemy
Since we are going to use MySQL in this post, we will also install a SQL connector for MySQL in Python. However, none of the code implementations changes with change in the database except for the SQL connectors.

pip install pymysql
Session in SQLAlchemy ORM
The Session establishes all conversations with the database. The session is a regular Python class which can be directly instantiated. However, to standardize how sessions are configured and acquired, the sessionmaker class is normally used to create a top-level Session configuration which can then be used throughout an application without the need to repeat the configurational arguments.

Syntax: sqlalchemy.orm.session.sessionmaker(bind=None, **kwargs)


Parameters:


bind: sqlalchemy.engine.Engine object specifying the database to perform conversations with.
Example 1: Creating a configured session class

import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql://root:password@\
localhost/Geeks4Geeks")

# CREATE THE TABLE MODEL TO USE IT FOR QUERYING
class Students(Base):

    __tablename__ = 'students'

    first_name = db.Column(db.String(50), 
                           primary_key=True)
    last_name  = db.Column(db.String(50), 
                           primary_key=True)
    course     = db.Column(db.String(50))
    score      = db.Column(db.Float)

# CREATE THE SESSION OBJECT
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()

# TESTING OUR SESSION OBJECT
result = session.query(Students).all()

for r in result:
    print(r.first_name, r.last_name)
Output:

Click to enlarge
Example 1 Output
For all the examples, we create a mandatory engine object so that we can bind the engine with the session. In this example, we have created a configured session object. The engine is defined at the time of the session maker call. However, there are other ways we can do it as per our requirements. The code uses a demo table for students which has 4 fields and 6 records as seen in the code and the output.

Example 2: Adding configurations to existing sessionmaker()

import sqlalchemy as db

# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql:/\
/root:password@localhost/Geeks4Geeks")

# CREATE THE SESSION OBJECT
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()

# session is configured later
Session.configure(bind=engine) 
session = Session()
In example 2, the session maker creates a session object. This session object is configured later as we can see in the program. This configure method comes in handy especially when we want to use multiple database instances or if the engine object is defined at a later stage in the program.

Example 3: Using multiple sessions in SQLAlchemy

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

# DEFINE THE ENGINE FOR DATABASE 1
engine_1 = db.create_engine("mysql+pymysql://\
root:password@localhost/Geeks4Geeks")

# DEFINE THE ENGINE FOR DATABASE 2
engine_2 = db.create_engine("mysql+pymysql://\
root:password@localhost/Geeks4Geeks2")

# CREATING A CONFIGURED SESSION
# CLASS FOR DATABASE 1
Session_1 = sessionmaker(bind=engine_1)
session_1 = Session_1()

# CREATING A SESSION CLASS FOR DATABASE
# 2 AND CONFIGURING IT LATER
Session_2 = sessionmaker()
Session_2.configure(bind=engine_2)
session_2 = Session_2()
In the third example, we have created 2 different sessions using the sessionmaker() method. Both these sessions are pointing to different database connections. In use cases like master-slave connection or multi-database architecture, this will prove to be a lot useful.