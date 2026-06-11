# ADR 06: Switching Data Access Layer to SQLAlchemy Connection Engine

## Status
Accepted

## Context
During the initiation of Phase 1 (Exploratory Data Analysis), we integrated Pandas (`pd.read_sql_query`) to fetch 90 days of sensor telemetry data into memory. 

Initially, the system utilized a raw, native database driver (`psycopg2`) utilizing a `RealDictCursor` to map relational rows into Python dictionaries. While functional for isolated, linear scripts, passing raw DBAPI2 connection handles directly into modern Pandas engines triggers explicit deprecation and safety warnings (`UserWarning: pandas only supports SQLAlchemy connectable...`).

Furthermore, as the application scales toward handling simultaneous API telemetry streams and concurrent asynchronous testing workloads, relying on raw, unmanaged database sockets presents severe production risks:
1. **Network Latency Overhead:** Opening and tearing down a distinct database socket connection for every single inbound API ping creates massive cryptographic and network handshake overhead.
2. **Socket Exhaustion:** High-frequency, concurrent sensor pings can quickly overwhelm PostgreSQL's connection limits, throwing `OperationalError: too many connections` crashes.

## Decision
We decided to replace raw `psycopg2` manual connection instantiations with a centralized **SQLAlchemy Engine Instance** across the analytical and feature engineering layers.

SQLAlchemy will act as an executive manager sitting on top of our low-level `psycopg2` driver. It will consume our project-isolated environment variables securely parsed from the local `.env` file via `python-dotenv`.

## Consequences

### Positive:
* **Connection Pooling:** SQLAlchemy automatically spins up and preserves a pool of open database connections in memory. Instead of destroying a socket when a query finishes, it returns the connection line to the pool for instant reuse by subsequent API calls, dropping connection latency down to nearly zero.
* **Dialect Abstraction:** Our Python code is now decoupled from the underlying database engine mechanics. If we migrate from PostgreSQL to a different relational or time-series data store in production later, we only need to alter the connection string protocol prefix, leaving our upstream Pandas feature-engineering code completely untouched.
* **Standard Integration:** Resolves the Pandas `UserWarning` entirely by using a native, explicitly tested engine framework.

### Negative / Trade-offs:
* **Dependency Footprint:** Introduces an additional structural dependency (`sqlalchemy`) to our local environment, which must be tracked and mirrored in production requirement arrays.