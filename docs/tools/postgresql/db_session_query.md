SQLAlchemy db.session.query()
Last Updated : 23 Jul, 2025
In SQLAlchemy, session.query() can be used as a filter in a query to specify criteria for which rows should be returned. This is done using the expression module and the filter method of the query object. The expression module allows you to create an expression that can be used in a query. This can include mathematical equations, as well as other types of expressions such as string concatenation or boolean logic. The filter method is used to apply the expression as a filter to the query. This specifies which rows should be included in the results of the query based on the criteria defined in the expression. Here's an example of using a How to Use db.session.query() in SQLAlchemy using Python.

Creating an SQLAlchemy Engine and Session
In this example, we first create an SQLAlchemy engine and session, and then define a simple model called Example that has an id column and a value column. We then create the example table in the database using the create_all() method. Next, we insert some data into the table using the add() method of the session and commit the changes to the database.


from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Create a SQLAlchemy engine
engine = create_engine('sqlite:///example.db')

# Create a SQLAlchemy session
Session = sessionmaker(bind=engine)
session = Session()

# Define a SQLAlchemy model
Base = declarative_base()


class Example(Base):
    __tablename__ = 'example'
    id = Column(Integer, primary_key=True)
    value = Column(Integer)


# Create the example table
Base.metadata.create_all(engine)

# Insert some data into the example table
session.add(Example(value=1))
session.add(Example(value=2))
session.add(Example(value=3))
session.commit()

# Use a mathematical equation as a filter in a query
results = session.query(Example).filter(Example.value * 2 > 3).all()

# Print the results
for result in results:
    print(result.value)

# Output: 2, 3
Output:

2 3
Filter Results Based on session.query.filter() method
In this example, we use the filter() method to filter the results of a query based on the mathematical equation Example.value * 2 > 3. This equation returns True for values of Example.value that is greater than 1.5, and False for values of Example.value that is less than or equal to 1.5. The all() method returns all the results of the query that match the filter condition.


from sqlalchemy import and_, or_
# Use multiple mathematical equations as filters in a query
# Use a mathematical equation as a filter in a query
results = session.query(Example).filter(Example.value * 2 > 3).all()
for result in results:
    print(result.id, result.value)
Output:

2 2
3 3
Insert Bulk Data using bulk_insert_mappings() method
Here, we are creating another table called "students" in a database. The table has four columns: "id", "name", "dob", and "marks". The "id" column is set as the primary key and the "dob" column is of type Date. The "declarative_base" function is used to create a base class for declarative models which is then used to define the Student class and its properties as columns.
The "create_all" method is used to create the table in the database. Then, it creates a list of student data, with each student represented as a dictionary containing the student's id, name, dob, and marks. After that, it uses the bulk_insert_mappings method to insert all the students in the list into the student's table in one go. Finally, it uses the commit() method to save the changes to the database.


from sqlalchemy import and_
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import date
Base = declarative_base()


class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    dob = Column(Date)
    marks = Column(Integer)


Base.metadata.create_all(engine)
students_data = [
    {'id': 122, 'name': 'Jane Smith',
                'dob': date(2002, 2, 1), 'marks': 90},
    {'id': 19, 'name': 'Bob Johnson',
     'dob': date(2001, 3, 1), 'marks': 75},
    {'id': 168, 'name': 'Alice Davis',
                'dob': date(1999, 4, 1), 'marks': 80},
]

session.bulk_insert_mappings(Student, students_data)
session.commit()
Query Database using session.query().label() method
Here, we query a database for all students, and for each student, it calculates the sum of their marks (from the "marks" column in the "Student" table) using the "func.sum" function. It then groups the results by the student's id using the "group_by" method. The result is a tuple of the student object and their total marks, which is then looped through and printed, displaying the student's name and their total marks.


from sqlalchemy import func

# add total marks obtained by each student in each subject
students = session.query(Student, 
                         func.sum(Student.marks).label(
    'total_marks')).group_by(Student.id).all()
for student_data in students:
    student = student_data[0]
    total_marks = student_data[1]
    print(student.name, total_marks)
Output:

Bob Johnson 75
Jane Smith 90
Alice Davis 80
Filter Students Based on Id and DOB using session.query.filter().all() method
This code uses the SQLAlchemy library to query a database for all students, and filter the results based on the following criteria: 

id >= 100 and id <= 200
dob > '2000-01-01'

The "and_" function is used to combine the two filter conditions on the 'id' and 'dob' columns of the "Student" table. The result is a list of student objects that match the specified criteria, which is then looped through and printed, displaying the student's name, date of birth, and marks.


students = session.query(Student).filter(
    and_(Student.id >= 100, Student.id <= 200,
         Student.dob > '2000-01-01')).all()
for student in students:
    print(student.name, student.dob, student.marks)
Output:

Jane Smith 2002-02-01 90
Filter Results Based on session.query.filter().count() method
This code uses the SQLAlchemy library to query a database for all students and count the number of students in the table. The "count()" method is used to count the number of students returned by the query. The result is a single integer value representing the total number of students in the table, which is then printed.


total_students = session.query(Student).count()
print(total_students)
Output:

3