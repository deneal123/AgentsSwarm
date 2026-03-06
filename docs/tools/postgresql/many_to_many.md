SQLAlchemy Core - Multiple Tables
Last Updated : 28 Feb, 2026
SQLAlchemy is an open-source library that provides a set of tools for working with relational databases. It offers a high-level Object-Relational Mapping (ORM) interface as well as a lower-level SQL Expression Language (Core) interface. SQLAlchemy Core is a lightweight and flexible SQL toolkit that provides a way to interact with relational databases using Python. In this article, we will explore how to work with multiple tables in SQLAlchemy Core and show some examples.

When working with a relational database, it's common to have multiple tables that are related to each other. For example, we might have a "students" table and a "fees" table, where each student has multiple fees associated with them. In SQLAlchemy Core, we can define multiple tables and create relationships between them.

Click to enlarge
Database Viewer
Example 1: 

Let's start with an example of defining two tables and creating a relationship between them. We'll create a "students" table and a "fees" table. Each student will have a unique ID, name, and age. Each fee will have a unique ID, amount, and a foreign key to the student ID.

In the below code, we have defined two tables - "students" and "fees". The "students" table has three columns - "id", "name", and "age". The "fees" table has three columns - "id", "amount", and "student_id". The "student_id" column is a foreign key that references the "id" column in the "students" table.

We have also defined a relationship between the two tables using the relationship function. The relationship function takes the name of the other table as an argument and defines the relationship between them.


from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///gfg.db', echo=True)
Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    
    fees = relationship("Fee", back_populates="student")
    
class Fee(Base):
    __tablename__ = 'fees'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Integer)
    student_id = Column(Integer, ForeignKey('students.id'))

    student = relationship("Student", back_populates="fees")

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

s1 = Student(name='John Doe', age=20)
s1.fees = [
    Fee(amount=100),
    Fee(amount=200)
]

session.add(s1)
session.commit()

student_fees = session.query(Student).filter_by(name='John Doe').one().fees

for fee in student_fees:
    print(fee.amount)
Output:

Click to enlarge
output1
Example 2:

In this example, we have defined two tables: Student and Fees. The Student table has id, name, and age columns, and the Fees table has id, amount, and student_id columns. There is a one-to-many relationship between Students and Fees, where one student can have multiple fees.

To join these two tables, we use the join method of the query object. We specify the Fees table and the condition for the join using the join method. In this case, we join the two tables on the student_id column of the Fees table and the id column of the Student table.

We also use the order_by method to order the results by the name column of the Student table and the amount column of the Fees table.

Finally, we print the result, which is a list of tuples containing the name and amount of each student's fees.

This example demonstrates how to use SQLAlchemy Core to join multiple tables and retrieve data from them.


from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    fees = relationship('Fee', back_populates='student')

class Fee(Base):
    __tablename__ = 'fees'
    id = Column(Integer, primary_key=True)
    amount = Column(Integer)
    student_id = Column(Integer, ForeignKey('students.id'))
    student = relationship('Student', back_populates='fees')

engine = create_engine('sqlite:///debo.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

students = [
    Student(name='John Doe', age=20),
    Student(name='Jane Smith', age=22),
    Student(name='Bob Brown', age=25),
    Student(name='Alice Jones', age=23)
]

fees = [
    Fee(amount=5000),
    Fee(amount=6000),
    Fee(amount=4500),
    Fee(amount=5500)
]

for i in range(len(students)):
    students[i].fees.append(fees[i])
    session.add(students[i])

session.commit()

from sqlalchemy.orm import joinedload

# Query all students and their fees using joinedload
students = session.query(Student).options(joinedload(Student.fees)).all()

for student in students:
    print(f'{student.name} ({student.age}):')
    for fee in student.fees:
        print(f'- {fee.amount}')

# Query students and fees using a join
from sqlalchemy.orm import aliased

student = aliased(Student)
fee = aliased(Fee)
stmt = session.query(student, fee)\
              .join(fee, student.id == fee.student_id)\
              .order_by(student.name)\
              .all()

for s, f in stmt:
    print(f'{s.name} ({s.age}): {f.amount}')
Output:

Click to enlarge
output2