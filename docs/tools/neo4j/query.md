Query the database
Once you have connected to the database, you can run queries using Cypher and the method Driver.execute_query().

Write to the database
To create two nodes representing persons named Alice and David, and a relationship KNOWS between them, use the Cypher clause CREATE:

Create two nodes and a relationship
summary = driver.execute_query(""" 
    CREATE (a:Person {name: $name})
    CREATE (b:Person {name: $friendName})
    CREATE (a)-[:KNOWS]->(b)
    """,
    name="Alice", friendName="David",  
    database_="<database-name>",  
).summary
print("Created {nodes_created} nodes in {time} ms.".format(
    nodes_created=summary.counters.nodes_created,
    time=summary.result_available_after
))
The Cypher query
The query parameters, as keyword arguments
The database to run the query on
Read from the database
To retrieve information from the database, use the Cypher clause MATCH:

Retrieve all Person nodes who like other Person s
records, summary, keys = driver.execute_query("""
    MATCH (p:Person)-[:KNOWS]->(:Person)
    RETURN p.name AS name
    """,
    database_="<database-name>",
)

# Loop through results and do something with them
for record in records:  
    print(record.data())  # get record as dict

# Summary information  
print("The query `{query}` returned {records_count} records in {time} ms.".format(
    query=summary.query, records_count=len(records),
    time=summary.result_available_after
))
records contains the result as an array of Record objects
summary contains the summary of execution returned by the server
Update the database
To update an entity’s information in the database, use the Cypher clauses MATCH and SET:

Update node Alice to add an age property
records, summary, keys = driver.execute_query("""
    MATCH (p:Person {name: $name})
    SET p.age = $age
    """, name="Alice", age=42,
    database_="<database-name>",
)
print(f"Query counters: {summary.counters}.")
To create a new relationship, linking it to two already existing node, use a combination of the Cypher clauses MATCH and CREATE:

Create a relationship :KNOWS between Alice and Bob
records, summary, keys = driver.execute_query("""
    MATCH (alice:Person {name: $name})  
    MATCH (bob:Person {name: $friend})  
    CREATE (alice)-[:KNOWS]->(bob)  
    """, name="Alice", friend="Bob",
    database_="<database-name>",
)
print(f"Query counters: {summary.counters}.")
Retrieve the person node named Alice and bind it to a variable alice
Retrieve the person node named Bob and bind it to a variable bob
Create a new :KNOWS relationship outgoing from the node bound to alice and attach to it the Person node named Bob
Delete from the database
To remove a node and any relationship attached to it, use the Cypher clause DETACH DELETE:

Remove the Alice node
# This does not delete _only_ p, but also all its relationships!
records, summary, keys = driver.execute_query("""
    MATCH (p:Person {name: $name})
    DETACH DELETE p
    """, name="Alice",
    database_="<database-name>",
)
print(f"Query counters: {summary.counters}.")
Query parameters
Do not hardcode or concatenate parameters directly into queries. Instead, always use placeholders and provide dynamic data as Cypher parameters. This is for:

performance benefits: Neo4j compiles and caches queries, but can only do so if the query structure is unchanged;

security reasons: see protecting against Cypher injection.

Query parameters can be passed either as several keyword arguments, or grouped together in a dictionary passed as value to the parameters_ keyword argument. In case of mix, keyword-argument parameters take precedence over dictionary ones.

Pass query parameters as keyword arguments
driver.execute_query(
    "MERGE (:Person {name: $name})",
    name="Alice", age=42,
    database_="<database-name>",
)
Pass query parameters in a dictionary
parameters = {
    "name": "Alice",
    "age": 42
}
driver.execute_query(
    "MERGE (:Person {name: $name})",
    parameters_=parameters,
    database_="<database-name>",
)
None of your keyword query parameters may end with a single underscore. This is to avoid collisions with the keyword configuration parameters. If you need to use such parameter names, pass them in the parameters_ dictionary.

There can be circumstances where your query structure prevents the usage of parameters in all its parts. For those rare use cases, see Dynamic values in property keys, relationship types, and labels.
Error handling
A query run may fail for a number of reasons, with different exceptions being raised. When using driver.execute_query(), the driver automatically retries to run a failed query if the failure is deemed to be transient (for example due to temporary server unavailability).

An exception will be raised if the operation keeps failing after the configured maximum retry time.

All exceptions coming from the server are subclasses of Neo4jError. You can use an exception’s code to stably identify a specific error; error messages are instead not stable markers, and should not be relied upon.

Basic error handling
# from neo4j.exceptions import Neo4jError

try:
    driver.execute_query('MATCH (p:Person) RETURN', database_='<database-name>')
except Neo4jError as e:
    print('Neo4j error code:', e.code)
    print('Exception message:', e.message)
'''
Neo4j error code: Neo.ClientError.Statement.SyntaxError
Exception message: Invalid input '': expected an expression, '*', 'ALL' or 'DISTINCT' (line 1, column 24 (offset: 23))
"MATCH (p:Person) RETURN"
                        ^
'''
Exception objects also expose errors as GQL-status objects. The main difference between Neo4j error codes and GQL error codes is that the GQL ones are more granular: a single Neo4j error code might be broken in several, more specific GQL error codes.

The actual cause that triggered an exception is sometimes found in the optional GQL-status object __cause__, which is itself an exception (or None). You might need to recursively traverse the cause chain before reaching the root cause of the exception you caught. In the example below, the exception’s GQL status code is 42001, but the actual source of the error has status code 42I06.

Usage of Neo4jError with GQL-related methods
# from neo4j.exceptions import Neo4jError

try:
    driver.execute_query('MATCH (p:Person) RETURN', database_='<database-name>')
except Neo4jError as e:
    print('Exception GQL status:', e.gql_status)
    print('Exception GQL status description:', e.gql_status_description)
    print('Exception GQL classification:', e.gql_classification)
    print('Exception GQL cause:', e.__cause__)
    print('Exception GQL diagnostic record:', e.diagnostic_record)
'''
Exception GQL status: 42001
Exception GQL status description: error: syntax error or access rule violation - invalid syntax
Exception GQL classification: GqlErrorClassification.CLIENT_ERROR
Exception GQL cause: {gql_status: 42I06} {gql_status_description: error: syntax error or access rule violation - invalid input. Invalid input '', expected: an expression, '*', 'ALL' or 'DISTINCT'.} {message: 42I06: Invalid input '', expected: an expression, '*', 'ALL' or 'DISTINCT'.} {diagnostic_record: {'_classification': 'CLIENT_ERROR', '_position': {'line': 1, 'column': 24, 'offset': 23}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}} {raw_classification: CLIENT_ERROR}
Exception GQL diagnostic record: {'_classification': 'CLIENT_ERROR', '_position': {'line': 1, 'column': 24, 'offset': 23}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}
'''
View all (2 more lines)
GQL status codes are particularly helpful when you want your application to behave differently depending on the exact error that was raised by the server.

Distinguishing between different error codes
# from neo4j.exceptions import Neo4jError

try:
    driver.execute_query('MATCH (p:Person) RETURN', database_='<database-name>')
except Neo4jError as e:
    if e.find_by_gql_status('42001'):
        # Neo.ClientError.Statement.SyntaxError
        # special handling of syntax error in query
        print(e.message)
    elif e.find_by_gql_status('42NFF'):
        # Neo.ClientError.Security.Forbidden
        # special handling of user not having CREATE permissions
        print(e.message)
    else:
        # handling of all other exceptions
        print(e.message)
The GQL status code 50N42 is returned when an exception does not have a GQL-status object. This can happen if the driver is connected to an older Neo4j server. Don’t rely on this status code, as future Neo4j server versions might change it with a more appropriate one.

Transient server errors can be retried without need to alter the original request. You can discover whether an error is transient via the method Neo4jError.is_retryable(), which gives insights into whether a further attempt might be successful. This is particular useful when running queries in explicit transactions, to know if a failed query is worth re-running.

Query configuration
You can supply further keyword arguments to alter the default behavior of .execute_query(). Configuration parameters are suffixed with _.

Database selection
Always specify the database explicitly with the database_ parameter, even on single-database instances. This allows the driver to work more efficiently, as it saves a network round-trip to the server to resolve the home database. If no database is given, the user’s home database is used.

driver.execute_query(
    "MATCH (p:Person) RETURN p.name",
    database_="<database-name>",
)
Specifying the database through the configuration method is preferred over the USE Cypher clause. If the server runs on a cluster, queries with USE require server-side routing to be enabled. Queries can also take longer to execute as they may not reach the right cluster member at the first attempt, and need to be routed to one containing the requested database.
Request routing
In a cluster environment, all queries are directed to the leader node by default. To improve performance on read queries, you can use the argument routing_="r" to route a query to the read nodes.

driver.execute_query(
    "MATCH (p:Person) RETURN p.name",
    routing_="r",  # short for neo4j.RoutingControl.READ
    database_="<database-name>",
)
Although executing a write query in read mode results in a runtime error, you should not rely on this for access control. The difference between the two modes is that read transactions will be routed to any node of a cluster, whereas write ones are directed to primaries. There is no security guarantee that a write query submitted in read mode will be rejected.

Run queries as a different user
You can execute a query through a different user with the parameter auth_. Switching user at the query level is cheaper than creating a new Driver object. The query is then run within the security context of the given user (i.e., home database, permissions, etc.).

driver.execute_query(
    "MATCH (p:Person) RETURN p.name",
    auth_=("<username>", "<password>"),
    database_="<database-name>",
)
The parameter impersonated_user_ provides a similar functionality. The difference is that you don’t need to know a user’s password to impersonate them, but the user under which the Driver was created needs to have the appropriate permissions.

driver.execute_query(
    "MATCH (p:Person) RETURN p.name",
    impersonated_user_="<username>",
    database_="<database-name>",
)
Transform query result
You can transform a query’s result into a different data structure using the result_transformer_ argument. The driver provides built-in methods to transform the result into a pandas dataframe or into a graph, but you can also craft your own transformer.

For more information, see Manipulate query results.

A full example
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


URI = "<database-uri>"
AUTH = ("<username>", "<password>")

people = [{"name": "Alice", "age": 42, "friends": ["Bob", "Peter", "Anna"]},
          {"name": "Bob", "age": 19},
          {"name": "Peter", "age": 50},
          {"name": "Anna", "age": 30}]

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    try:
        # Create some nodes
        for person in people:
            records, summary, keys = driver.execute_query(
                "MERGE (p:Person {name: $person.name, age: $person.age})",
                person=person,
                database_="<database-name>",
            )

        # Create some relationships
        for person in people:
            if person.get("friends"):
                records, summary, keys = driver.execute_query("""
                    MATCH (p:Person {name: $person.name})
                    UNWIND $person.friends AS friend_name
                    MATCH (friend:Person {name: friend_name})
                    MERGE (p)-[:KNOWS]->(friend)
                    """, person=person,
                    database_="<database-name>",
                )

        # Retrieve Alice's friends who are under 40
        records, summary, keys = driver.execute_query("""
            MATCH (p:Person {name: $name})-[:KNOWS]-(friend:Person)
            WHERE friend.age < $age
            RETURN friend
            """, name="Alice", age=40,
            routing_="r",
            database_="<database-name>",
        )
        # Loop through results and do something with them
        for record in records:
            print(record)
        # Summary information
        print("The query `{query}` returned {records_count} records in {time} ms.".format(
            query=summary.query, records_count=len(records),
            time=summary.result_available_after
        ))

    except Neo4jError as e:
        print(e)
        # further logging/processing
View all (41 more lines)
For more information see API documentation → Driver.execute_query().