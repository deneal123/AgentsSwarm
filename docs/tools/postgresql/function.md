SQLAlchemy Core - Functions
Last Updated : 23 Jul, 2025
SQLAlchemy provides a rich set of functions that can be used in SQL expressions to perform various operations and calculations on the data. SQLAlchemy provides the Function API to work with the SQL functions in a more flexible manner. The Function API is used to construct SQL expressions representing function calls and can be applied to columns. SQL functions are invoked by using the func namespace.

Prerequisites

SQLAlchemy Core – Creating Table
Querying and selecting specific columns in SQLAlchemy
SQLAlchemy Core - func Function
It is an object in SQLAlchemy that serves as a namespace for SQL functions.

Syntax: func.function_name(column).


Parameters:


func: It is an object in SQLAlchemy that serves as a namespace for SQL functions.
function_name(): Which represents the SQL function EX: avg, count, sum, max, min...
column: Represents a column of table in Database.
Return: returns a SQL Expression which represents the SQL function call with specified column.


For our examples, we have already created a Student table which we will be using:

Student-table
Students Table
SQLAlchemy Mathematical Functions
Python sqlalchemy func.avg(column)
This function Calculates the average value of all rows in a column. The below code connects to a MySQL database using SQLAlchemy, calculates the average score of students in a table named "student", and prints the result. Replace the database credentials and ensure the table and column names match your database schema.


from sqlalchemy import create_engine, MetaData,select,func
engine = create_engine("mysql+pymysql://userName:password@host:port/dbName")
metadata = MetaData()
metadata.reflect(bind=engine)
studentTable=metadata.tables['student']
query=select(func.avg(studentTable.c.score).label("Average"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Average of Student's score is::",result[0][0])
Output: In the example we are calculating the average value of scores students.

avg-Output
Avg output
Python sqlalchemy func.count(column)
Counts the NON-NULL values in a column. This code connects to a MySQL database using SQLAlchemy, counts the number of students in a table named "student", and prints the result. Make sure to replace the database credentials and ensure the table and column names match your database schema.


query=select(func.count(studentTable.c.name).label("Count of Students"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Total count of students in class::",result[0][0])
Output:

countOutput
Count Output
Python sqlalchemy func.sum(column)
Calculates the sum of values in a column. This code connects to a MySQL database using SQLAlchemy, calculates the sum of scores from a table named "student", and prints the result. Make sure to replace the database credentials and ensure the table and column names match your database schema.


query=select(func.sum(studentTable.c.score).label("Sum of scores"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Sum of scores of students::",result[0][0])
Output

sumOutput
Sum Output
Python sqlalchemy func.max(column_name)
Finds the max value in the given column.

This code connects to a MySQL database using SQLAlchemy, calculates the maximum score from a table named "student", and prints the result. Make sure to replace the database credentials and ensure the table and column names match your database schema.


query=select(func.max(studentTable.c.score).label("Max Score"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Maximum Score in Student scores::",result[0][0])
Output

FuncMax-op
Max Output
Python sqlalchemy max.group_by
In this example we are grouping the students by Grade and then finding the max score in corresponding group


query=select(studentTable.c.grade, func.max(studentTable.c.score).
             label("maxscore")).group_by(studentTable.c.grade)
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("grade || max score")
    for data in result:
      print(data[0],"||",data[1])
Output:

FuncMax2
Max with Group By output
Python sqlalchemy func.min(column_name)
Used to find the minimum value in column. In the following example we are calculating the minimum value in each grade and count of students in each grade.


query=select(studentTable.c.grade,func.min(studentTable.c.score),func.count(studentTable.c.score))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("grade | min value | count")
    for data in result:
      print(data[0],data[1],data[2])
      
Output:

FuncMin
Min output
Python sqlalchemy func.floor(Value)
The floor() function rounds down a numeric value to the nearest integer that is less than or equal to the original value. This code connects to a database using SQLAlchemy, calculates the floor value of 3.6 using the func.floor function, and prints the result




query=select(func.floor(3.6))
​
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Floor value of 3.6 is",result[0][0])
Output

Floor value of 3.6 is 3.0
Python sqlalchemy floor with avg
This code uses SQLAlchemy to connect to a database, calculates the average of the score column in the studentTable, and then rounds the result to the nearest integer using the func.floor function. Finally, it prints the result, which is the average score of students rounded to the nearest integer.


query=select(func.floor(func.avg(studentTable.c.score)).label("Average"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    print("Average of Student's score rounded to nearest integer::",result[0][0])
Output
Funcfloor

Python sqlalchemy func.abs(Value):
abs() function to calculate the absolute value of a numeric expression. The func.abs() function takes a single argument, which can be a numeric value and returns its absolute value.


query=select(func.abs(10),literal(10),func.abs(-20),literal(-20),func.abs(30+43-100),literal(30+43-100))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
print("Abs values of abs value and actual value::",*result[0])
Output



Funcabs
Abs output

SQLAlchemy Core - String Functions
Python sqlalchemy func.length(column):
Returns the length of a string column. This code selects the name column from the studentTable and calculates the length (number of characters) of each name using the func.length function. It then labels the calculated length as "Sum of scores". The code executes the query, retrieves the results, and iterates through the rows to print each student's name and the length of their name (character count).


query=select(studentTable.c.name,func.length(studentTable.c.name).label("Sum of scores"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0],data[1])
Output

lengthOutput

Python sqlalchemy func.lower(column)
It returns the lower case of given string.

This code selects the name column from the studentTable and converts the names to lowercase using the func.lower function. The code executes the query, retrieves the results, and prints each student's name in lowercase.


query=select(func.lower(studentTable.c.name).label("Upper"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0])
Output



lowerOutput
lower outut


Python sqlalchemy func.upper(column)
Returns the Upper case of given string.

This code selects the name column from the studentTable and converts the names to uppercase using the func.upper function. The code executes the query, retrieves the results, and prints each student's name in uppercase.


query=select(func.upper(studentTable.c.name).label("Upper"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0])
Output



upperOutput
Upper Output


SQLAlchemy Core - Date and Time Functions
Python sqlalchemy func.now()
Returns todays date and current time as result. This code selects the current timestamp using func.now() and labels it as "now". It then executes the query, retrieves the result, and prints the current timestamp, which represents the current date and time.


query=select(func.now().label("now"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0])
Output

nowOutput

Python sqlalchemy func.current_time()
Returns the current time. This code selects the current date and time using func.current_date() and func.current_time(). It labels the date as "date" and the time as "time". It then executes the query, retrieves the result, and prints the current date and time.


query=select(func.current_date().label("date"),func.current_time().label("time"))
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0],data[1])
Output:

nowOutput


SQLAlchemy Core - Other Functions
Python sqlalchemy func.group_concat(column, separator)
This function is used to concatenate string from multiple rows into a single string using various clauses. When we using the group_by clause a single row may contains multiple values. If your are not using the group_concat() function we can see only one value in result instead of getting the all the values. So we can group_concat() to get the all string values in group. In the following example we are grouping the students based on their grades and retrieving the results by group_concat() method.


query = select(
    studentTable.c.grade,
    func.group_concat(studentTable.c.name, ',').label('names')
).group_by(studentTable.c.grade)
with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(data[0],data[1])
Output

groupConcate

Python sqlalchemy case()
case() function is used to construct a SQL CASE expression within your queries. The CASE expression allows you to conditionally evaluate and return different values based on specified conditions.

Syntax: 
case(
(condition1,vlaue1),
(condition2,value2),
........
else_=default_value
)

In the following example we are assigning grade points to student based on score


query = select(
    studentTable.c.name,studentTable.c.score,
    case(
            (and_(studentTable.c.score>=91,studentTable.c.score<=100),10),
            (and_(studentTable.c.score>=81, studentTable.c.score<=90) , 9),
            (and_(studentTable.c.score>=71, studentTable.c.score<=80) , 8),
            (and_(studentTable.c.score>=61, studentTable.c.score<=70) , 7),
            (and_(studentTable.c.score>=51, studentTable.c.score<=60) , 6),
            (and_(studentTable.c.score>=41, studentTable.c.score<=50) , 5),
            else_=0
    ).label("Grade Points")
)

with engine.connect() as connect:
    result=connect.execute(query).fetchall()
    for data in result:
        print(*data)
Output

CaseEx