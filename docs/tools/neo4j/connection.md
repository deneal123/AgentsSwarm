Connection
Once you have installed the driver and have a running Neo4j instance, you are ready to connect your application to the database.

Connect to the database
You connect to a database by creating a Driver object and providing a URL and your login credentials.

from neo4j import GraphDatabase

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "<database-uri>"
AUTH = ("<username>", "<password>")

with GraphDatabase.driver(URI, auth=AUTH) as driver: 
    driver.verify_connectivity() 
    print("Connection established.")
Creating a Driver instance only provides information on how to access the database, but does not actually establish a connection. Connection is instead deferred to when the first query is executed.
To verify immediately that the driver can connect to the database (valid credentials, compatible versions, etc), use the .verify_connectivity() method after initializing the driver. In case of failure, enabling the driver’s logs can help diagnosing the issue.
Both the creation of a Driver object and the connection verification can raise a number of different exceptions. Since error handling can get quite verbose, and a connection error is a blocker for any subsequent task, a common choice is to let the program crash should an exception occur during connection.

Driver objects are immutable, thread-safe, and expensive to create, so your application should create only one instance and pass it around (you can share Driver instances across threads). If you need to query the database through several different users, use impersonation without creating a new Driver instance. If you want to alter a Driver configuration, you need to create a new object.

The driver also supports other authentication methods (kerberos, bearer, custom).
Connect to an Aura instance
When you create an Aura instance, you get to download a text file (a so-called Dotenv file) containing the connection information to the database as environment variables. The file has a name of the form Neo4j-a0a2fa1d-Created-2023-11-06.txt.

You can either manually extract the URI and the credentials from that file, or use a third party-package (ex. python-dotenv) to load them.

import dotenv
import os
from neo4j import GraphDatabase

load_status = dotenv.load_dotenv("Neo4j-a0a2fa1d-Created-2023-11-06.txt")
if load_status is False:
    raise RuntimeError('Environment variables not loaded.')

URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()
    print("Connection established.")
An Aura instance is not conceptually different from any other Neo4j instance, as Aura is simply a deployment mode for Neo4j. When interacting with a Neo4j database through the driver, it doesn’t make a difference whether it is an Aura instance it is working with or a different deployment.
Connect to a cluster
When working with a Neo4j cluster, you have a few options to connect to it, depending on how it’s deployed.

Upon connection, the driver gets a routing table containing information about all the machines in the cluster (including their roles), and will point requests to primaries or secondaries as needed. The routing table is periodically refreshed.

If the cluster members are all discoverable via a hostname that provides multiple A/AAAA records, you can use the hostname and port.

If the addresses of the cluster members are known, but not advertised via A/AAAA records, you can use a Custom address resolver to extend the DNS resolution on the client side.

from neo4j import GraphDatabase


def custom_resolver(socket_address):
    yield "server01.example.com", 7687
    yield "server02.example.com", 7687
    yield "server03.example.com", 7687
    yield "backup.example.org", 7687


driver = GraphDatabase.driver(
    "neo4j://example.com:7687", auth=(USERNAME, PASSWORD),
    resolver=custom_resolver)
You can also use the address of any machine belonging to the cluster: the driver will discover the others. This is the least fail-safe option, because if the machine you use as entrypoint becomes unavailable, the driver won’t be able to fetch a routing table.

You can also bypass the routing table and connect to a specific machine in the cluster using its address together with the bolt[+s[sc]]:// scheme (see connection URI for more information).

Close connections
Always close Driver objects to free up all allocated resources, even upon unsuccessful connection or runtime errors. Either instantiate the Driver object using the with statement, or call the Driver.close() method explicitly.

Further connection parameters
For more Driver configuration parameters and further connection settings, see Advanced connection information.