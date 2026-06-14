# ADR 06: Standardizing Database Access Through SQLAlchemy Engine

## Status

Accepted

## Context

During the initiation of Phase 1 (Exploratory Data Analysis), the project integrated Pandas (`pd.read_sql_query`) to retrieve and analyze approximately 90 days of telemetry data stored in PostgreSQL.

The original implementation relied on direct `psycopg2` database connections and `RealDictCursor` objects. While this approach was sufficient for simple scripts and one-off database operations, it introduced limitations as the project expanded into exploratory analysis, feature engineering pipelines, automated testing, and future API-driven ingestion workflows.

The immediate catalyst for change was Pandas generating explicit warnings when interacting directly with raw DBAPI2 connections:

```text
UserWarning:
pandas only supports SQLAlchemy connectable...
```

This warning reflects the fact that modern Pandas integrations are designed and tested primarily against SQLAlchemy connection engines rather than unmanaged driver-level connections.

Beyond compatibility concerns, maintaining direct database connections across multiple project components creates operational risks as the system grows:

1. **Connection Management Complexity:** Each script or service becomes responsible for opening, maintaining, and closing database sessions correctly.
2. **Connection Overhead:** Establishing a new PostgreSQL session for every operation introduces unnecessary network and authentication overhead.
3. **Connection Exhaustion Risk:** As concurrent workloads increase, unmanaged connection creation can consume PostgreSQL connection limits and trigger operational failures.
4. **Code Duplication:** Database connection logic becomes scattered throughout notebooks, scripts, tests, and future API services.

---

## Decision

We decided to standardize database access through a centralized SQLAlchemy Engine.

SQLAlchemy acts as a high-level database access layer while continuing to use the PostgreSQL driver (`psycopg2`) underneath. Connection configuration is sourced from environment variables managed through `.env` and `python-dotenv`.

All analytical notebooks, feature engineering pipelines, database initialization scripts, and future application services will acquire database connectivity through a shared engine creation pattern rather than instantiating raw driver connections directly.

Example:

```python
engine = create_engine(
    db_url,
    pool_pre_ping=True
)
```

This engine becomes the project's canonical database access interface.

---

## Consequences

### Positive

#### Standard Pandas Integration

Pandas natively supports SQLAlchemy engines for SQL operations.

Using a SQLAlchemy engine removes compatibility warnings and aligns the project with the officially supported integration path.

---

#### Connection Pooling

SQLAlchemy automatically manages a pool of reusable database connections.

Instead of repeatedly opening and destroying PostgreSQL sessions, completed connections are returned to the pool and reused by future operations.

This significantly reduces the overhead associated with repeatedly establishing new database sessions.

---

#### Centralized Database Access Layer

Database connectivity is now standardized behind a single abstraction layer.

The same engine pattern is used across:

* Database initialization scripts
* Exploratory Data Analysis notebooks
* Feature engineering pipelines
* Model training workflows
* Future FastAPI services

This reduces duplicated connection-management code throughout the repository.

---

#### Reduced Operational Risk

Connection pooling helps protect the application from unnecessary connection growth under concurrent workloads.

By reusing existing sessions instead of creating new ones for every operation, the system becomes more resilient as ingestion and analytical workloads increase.

---

#### Reduced Database Coupling

SQLAlchemy provides a consistent interface across multiple relational database systems.

Migration between supported relational databases requires significantly fewer application changes because most upstream query and data-access code remains unchanged.

---

### Negative / Trade-offs

#### Additional Dependency

The project now depends on SQLAlchemy in addition to the PostgreSQL driver.

This increases the dependency footprint and requires version management across development, testing, and deployment environments.

---

#### Additional Abstraction Layer

SQLAlchemy introduces an additional layer between application code and the underlying database driver.

While generally beneficial, debugging low-level database behavior can occasionally require understanding both SQLAlchemy and the underlying PostgreSQL driver.

---

#### Not a Complete Portability Guarantee

Although SQLAlchemy reduces database-specific coupling, migration to fundamentally different storage engines (such as dedicated time-series databases) would still require application and schema-level changes.

The abstraction simplifies migration but does not eliminate it entirely.

---

## Outcome

The project now uses a standardized, pooled, and Pandas-compatible database access layer that supports current analytical workloads while providing a scalable foundation for future ingestion APIs, feature engineering services, and real-time anomaly detection components.
