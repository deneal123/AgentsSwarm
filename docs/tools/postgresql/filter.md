How to get specific columns in SQLAlchemy with filter?
Last Updated : 4 Jan, 2022
In this article, we will see how to query and select specific columns using SQLAlchemy in Python.

For our examples, we have already created a Students table which we will be using:

Click to enlarge
Students Table
Selecting specific column in SQLAlchemy based on filter:
To select specific column in SQLAlchemy
Syntax: sqlalchemy.select(*entities)


entities: Entities to SELECT from. This is typically a series of ColumnElement for Core usage and ORM-mapped classes for ORM usage.


To filter records in SQLAlchemy

Syntax: sqlalchemy.query.filter(*criterion)


criterion: Criterion is one or more criteria for selecting the records.


Example 1: Selecting specific column based on a single filter

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql://\
root:password@localhost/Geeks4Geeks")

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
Session = sessionmaker(bind=engine)
session = Session()

# SELECTING COLUMN `first_name`, `last_name` WHERE `score > 80`
result = session.query(Students) \
    .with_entities(Students.first_name, Students.last_name) \
        .filter(Students.score > 80).all()

for r in result:
    print(r.first_name, r.last_name)
Output:

Click to enlarge
Output - Example 1
Example 2: Selecting a specific column based on multiple filters

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# DEFINE THE ENGINE (CONNECTION OBJECT)
engine = db.create_engine("mysql+pymysql://\
root:password@localhost/Geeks4Geeks")

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
Session = sessionmaker(bind=engine)
session = Session()

# SELECTING COLUMN `first_name`, `score`
# WHERE `score > 80` AND `course` is STATISTICS
result = session.query(Students) \
    .with_entities(Students.first_name, Students.score) \
        .filter(Students.score > 80,
                Students.course.like('Statistics')).all()

for r in result:
    print(r.first_name, r.score)
Output:

Click to enlarge