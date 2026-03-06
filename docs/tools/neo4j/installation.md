Installation
To start creating a Neo4j Python application, you first need to install the Python Driver and get a Neo4j database instance to connect to.

Install the driver
Use pip to install the Neo4j Python Driver (requires Python >= 3.10):

pip install neo4j
The latest version of the driver is guaranteed to work with all LTS releases of the Neo4j server, as well as with the current and next major releases. The latest 6.x driver supports connection to Neo4j instances version 4.4, 5.x, and 2025.x. For a detailed list of changes across versions, see the driver’s changelog.

Activate Python’s development mode
The Rust extension to the Python driver is an alternative package that yields a 3x to 10x speedup compared to the regular driver. You can install it with pip install neo4j-rust-ext, either alongside the neo4j package or as a replacement to it. Usage-wise, the libraries are identical: everything in this guide applies to both.
To get the driver on an air-gapped machine, download the latest driver tarball and install it with pip install neo4j-<version>.tar.gz.
Get a Neo4j instance
You need a running Neo4j database in order to use the driver with it. The easiest way to spin up a local instance is through a Docker container (requires docker.io). The command below runs the latest Neo4j version in Docker, setting the admin username to neo4j and password to secretgraph:

docker run \
   -p7474:7474 \                       # forward port 7474 (HTTP)
   -p7687:7687 \                       # forward port 7687 (Bolt)
   -d \                                # run in background
   -e NEO4J_AUTH=neo4j/secretgraph \   # set login credentials
   neo4j:latest
Alternatively, you can obtain a free cloud instance through Aura.

You can also install Neo4j on your system, or use Neo4j Desktop to create a local development environment (not for production).