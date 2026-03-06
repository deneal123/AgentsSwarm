Manipulate query results
This section shows how to work with a query’s result so as to extract data in the form that is most convenient for your application.

Result as a list
By default, Driver.execute_query() returns an EagerResult object.

records, summary, keys = driver.execute_query(
    "MATCH (a:Person) RETURN a.name AS name, a.age AS age",
    database_="<database-name>",
)
for person in records:  
    print(person)
    # person["name"] or person["age"] are also valid

# Some summary information  
print("Query `{query}` returned {records_count} records in {time} ms.".format(
    query=summary.query, records_count=len(records),
    time=summary.result_available_after
))

print(f"Available keys are {keys}")  # ['name', 'age'] 
The result records come in a list.
A summary of execution, with metadata and information about the result.
The keys available in the returned rows.
Transform to Pandas DataFrame
The driver can transform the result into a Pandas DataFrame by setting result_transformer_=neo4j.Result.to_df. This method requires the pandas library is installed.

Return a DataFrame with two columns (n, m) and 10 rows
import neo4j

pandas_df = driver.execute_query(
    "UNWIND range(1, 10) AS n RETURN n, n+1 AS m",
    database_="<database-name>",
    result_transformer_=neo4j.Result.to_df
)
print(type(pandas_df))  # <class 'pandas.core.frame.DataFrame'>
This transformer accepts two optional arguments:

expand — If True, some data structures in the result will be recursively expanded and flattened. More info in the API documentation.

parse_dates — If True, columns exclusively containing time.DateTime objects, time.Date objects, or None, will be converted to pandas.Timestamp.

To pass parameters to to_df, use lambda functions:
result_transformer_=lambda res: res.to_df(True)
Transform to graph
The driver can transform the result into a collection of graph objects by setting result_transformer_=neo4j.Result.graph. To make the most out of this method, your query should return a graph-like result instead of a single column. The graph transformer returns a Graph object exposing the properties nodes and relationships, which are set views into Node and Relationship objects.

You can use the graph format for further processing or to visualize the query result. An example implementation that uses the pyvis library to draw the graph is below.

Visualize graph result with pyvis
import pyvis
from neo4j import GraphDatabase
import neo4j


URI = "<database-uri>"
AUTH = ("<username>", "<password>")


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        # Create some friends
        input_list = [("Arthur", "Guinevre"),
                      ("Arthur", "Lancelot"),
                      ("Arthur", "Merlin")]
        driver.execute_query("""
            UNWIND $pairs AS pair
            MERGE (a:Person {name: pair[0]})
            MERGE (a)-[:KNOWS]->(friend:Person {name: pair[1]})
            """, pairs=input_list,
            database_="<database-name>",
        )

        # Create a film
        driver.execute_query("""
            MERGE (film:Film {title: $title})
            MERGE (liker:Person {name: $person_name})
            MERGE (liker)-[:LIKES]->(film)
            """, title="Wall-E", person_name="Arthur",
            database_="<database-name>",
        )

        # Query to get a graphy result
        graph_result = driver.execute_query("""
            MATCH (a:Person {name: $name})-[r]-(b)
            RETURN a, r, b
            """, name="Arthur",
            result_transformer_=neo4j.Result.graph,
        )

        # Draw graph
        nodes_text_properties = {  # what property to use as text for each node
            "Person": "name",
            "Film": "title",
        }
        visualize_result(graph_result, nodes_text_properties)


def visualize_result(query_graph, nodes_text_properties):
    visual_graph = pyvis.network.Network()

    for node in query_graph.nodes:
        node_label = list(node.labels)[0]
        node_text = node[nodes_text_properties[node_label]]
        visual_graph.add_node(node.element_id, node_text, group=node_label)

    for relationship in query_graph.relationships:
        visual_graph.add_edge(
            relationship.start_node.element_id,
            relationship.end_node.element_id,
            title=relationship.type
        )

    visual_graph.show('network.html', notebook=False)


if __name__ == "__main__":
    main()
View all (53 more lines)
pyvis example
Figure 1. Graph visualization of example above
Custom transformers
For more advanded scenarios, you can use the parameter result_transformer_ to provide a custom function that further manipulates the Result object resulting from your query. A transformer takes a Result object and can output any data structure. The transformer’s return value is in turn returned by .execute_query().

Inside a transformer function you can use any of the Result methods.

A custom transformer using single and consume
# Get a single record (or an exception) and the summary from a result.
def get_single_person(result):
    record = result.single(strict=True)
    summary = result.consume()
    return record, summary


record, summary = driver.execute_query(
    "MERGE (a:Person {name: $name}) RETURN a.name AS name",
    name="Alice",
    database_="<database-name>",
    result_transformer_=get_single_person,
)
print("The query `{query}` returned {record} in {time} ms.".format(
      query=summary.query, record=record, time=summary.result_available_after))
A custom transformer using fetch and peek
# Get exactly 5 records, or an exception.
def exactly_5(result):
    records = result.fetch(5)

    if len(records) != 5:
        raise Exception(f"Expected exactly 5 records, found only {len(records)}.")
    if result.peek():
        raise Exception("Expected exactly 5 records, found more.")

    return records


records = driver.execute_query("""
    UNWIND ['Alice', 'Bob', 'Laura', 'John', 'Patricia'] AS name
    MERGE (a:Person {name: name}) RETURN a.name AS name
    """, database_="<database-name>",
    result_transformer_=exactly_5,
)
View all (3 more lines)
A transformer must not return the Result object itself. Doing so is roughly equivalent to returning a pointer to the result buffer, which gets invalidated as soon as the query’s transaction is over.

def transformer(result):
    return result

result = driver.execute_query(
    "MATCH (a:Person) RETURN a.name",
    result_transformer_=transformer)
print(result)
print(result.single())
neo4j.exceptions.ResultConsumedError: The result is out of scope.
The associated transaction has been closed.
Results can only be used while the transaction is open.