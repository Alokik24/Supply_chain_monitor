# Phase 2: Turning an Offline Pipeline into a Running System

By the end of Phase 1, I had a working anomaly detection pipeline, but everything still existed offline. The models operated on historical datasets and generated predictions inside notebooks. The next challenge was figuring out how a real telemetry event would enter the system and eventually reach the analytical pipeline.

This phase started with a simple goal: build an ingestion service capable of receiving telemetry, validating it, and storing it reliably.

## Building the Ingestion Layer

The first step was creating an API layer using FastAPI. On the surface, the workflow looked straightforward: receive a sensor reading, validate it, and store it in PostgreSQL.

While implementing the endpoint, I found myself revisiting many of the design decisions made earlier in the project. The wide-to-narrow telemetry transformation from ADR-05 suddenly became much more practical because the ingestion layer now had to persist individual sensor events rather than static CSV rows.

At the same time, I started thinking about duplicate events. During development it was easy to assume every reading would be unique, but real systems rarely behave that cleanly. Network retries, service restarts, or client-side bugs can easily produce duplicate submissions. Rather than handling those checks in application code, I pushed the responsibility into PostgreSQL through a composite uniqueness constraint and idempotent insert operations. It was one of the first times I saw how database design directly influences application behaviour.

---

## Discovering Async Programming

The part of this phase that took me the longest to understand wasn't FastAPI itself. It was asynchronous programming.

Before this project, most of my Python experience involved scripts that executed one operation at a time. Async code looked similar on the surface, but the execution model was very different.

I could follow the syntax:

```python
async def ...
await ...
```

but I didn't fully understand what was happening underneath.

That became obvious when I started writing integration tests.

Several tests would pass when executed individually but fail when run together. Error messages referred to event loops, pending futures, transaction contexts, and sessions attached to different loops. Initially, those errors felt completely disconnected from the code I had written.

The debugging process forced me to think about what FastAPI, SQLAlchemy, and asyncpg were actually doing behind the scenes. Requests were not simply executing from top to bottom. Multiple operations were sharing resources through an event loop, and the test environment had to manage those resources correctly.

I still wouldn't claim to fully understand every internal detail, but I left the phase with a much clearer mental model of why asynchronous applications require careful session management, dependency injection, and transaction boundaries.

---

## When the Architecture Met Docker

Up until this point, most of the project existed as Python code running on my machine. Docker changed that.

The goal was simple: run FastAPI, PostgreSQL, and Redis together inside a reproducible environment.

What surprised me was how many assumptions I had been making about networking.

I repeatedly treated containers as if they shared the same localhost. The reality was that Docker Compose creates an isolated network where services communicate through container names. Many of the connection issues I encountered were not application bugs at all. They were infrastructure problems caused by incorrect environment variables, hostnames, or startup assumptions.

The experience changed how I viewed deployment. Instead of thinking about individual programs, I started thinking about services communicating across a network.

---

## Building Confidence Through Testing

Once the ingestion path was working, I wanted something stronger than manual API calls.

That led to the integration test suite.

The tests verified:

* Successful ingestion
* Request validation
* Duplicate event handling
* Database persistence

Writing the tests turned out to be harder than writing the endpoint itself. Most of the complexity came from isolating database transactions and ensuring that asynchronous resources behaved consistently across multiple test runs.

Although frustrating at times, the process exposed several hidden assumptions in the implementation and ultimately made the system far more reliable.

---

## End-to-End Validation

The final milestone of the phase was validating the entire ingestion pipeline under a realistic workload.

To do that, I built a replay engine capable of streaming the synthetic telemetry dataset through the live API. Instead of inserting records directly into PostgreSQL, every event traveled through the same path a real client would use.

The replay execution exercised:

* FastAPI
* Pydantic validation
* SQLAlchemy
* PostgreSQL
* Docker infrastructure
* Idempotency safeguards

The complete dataset contained 129,600 telemetry rows and became the first true end-to-end validation of the platform.

Watching the replay finish successfully was probably the moment the project felt most real. Up until then, the architecture largely existed in diagrams, ADRs, and isolated components. The replay engine demonstrated that those components could actually operate together as a system.

## Looking Back

At the start of Phase 2, I thought I was building an API.

Looking back, the API was only a small part of the work.

The larger challenge was understanding how applications, databases, containers, asynchronous execution, and testing infrastructure interact with one another. Many of the hardest problems were not machine learning problems at all. They were systems problems.

By the end of the phase, the project had moved beyond notebooks and offline experiments. For the first time, telemetry could enter the platform through a live interface, pass through validation, persist to a database, and be verified through automated testing.

The anomaly detection models may still be the final destination, but Phase 2 was where the project began to feel like a real system rather than a collection of scripts.

## Phase 2.2: Teaching the System to Think

By the end of the ingestion phase, telemetry could successfully enter the platform and be stored in PostgreSQL. Sensor events were flowing through the API, validation rules were working, and the replay engine could push the synthetic dataset through the system end-to-end.

The platform could receive data.

The platform could store data.

What it still couldn't do was understand any of it.

At that point, the anomaly detection models still existed largely as offline components. They could score historical datasets, but they weren't connected to the live telemetry pipeline. The next challenge was figuring out how incoming sensor readings would eventually become investigation cases.

### The First Architectural Fork

My initial instinct was to perform anomaly scoring directly inside the ingestion API.

A telemetry event would arrive, features would be generated, the model would execute, and the anomaly score would be returned immediately. On paper, it seemed like the most straightforward design.

The more I thought about it, however, the less comfortable it became.

The ingestion service existed for one purpose: accept telemetry and persist it reliably. The anomaly detection workflow had very different requirements. Before a score could even be generated, the system needed historical context, feature engineering, rolling statistics, and machine-state reconstruction. Those operations were computationally expensive and depended on significantly more data than a single incoming event.

Although both components worked with the same telemetry, they were solving fundamentally different problems.

The ingestion path wanted to be fast.

The scoring path wanted to be thorough.

Trying to force both concerns into the same request-response cycle would couple telemetry throughput directly to model execution time.

That realization eventually led to one of the largest architectural decisions in the project: separating the platform into a Hot Path and a Cold Path.

### Separating Ingestion from Analysis

The Hot Path became responsible only for accepting and storing telemetry.

The Cold Path became responsible for everything analytical.

A dedicated scoring worker would periodically wake up, retrieve newly arrived telemetry, reconstruct machine state, generate features, execute machine learning inference, and create anomaly cases.

Conceptually, the system evolved into:

```text
Telemetry
    ↓
Storage
    ↓
Scoring Worker
    ↓
Feature Engineering
    ↓
Model Inference
    ↓
Incident Creation
```

At first this felt like a more complicated architecture because it introduced another moving component into the system. Looking back, it actually simplified the overall design.

The ingestion service no longer needed to understand machine learning.

The scoring service no longer needed to worry about request latency.

Both parts of the platform could evolve independently while remaining connected through shared storage.

### Discovering the Watermark Problem

Once the worker existed, another question immediately appeared.

How would it know which telemetry had already been processed?

My first instinct was surprisingly naive: simply scan the entire telemetry table every time the worker executed.

That idea worked while the dataset was small, but it became obviously wasteful once I considered how the platform would behave over time. Reprocessing historical telemetry repeatedly would cause the amount of work performed by the worker to grow continuously, even when only a handful of new readings had arrived.

The worker needed memory.

Not machine-learning memory.

Operational memory.

That requirement eventually led to the watermark design.

Rather than marking individual records as processed, the worker stores the highest successfully evaluated telemetry identifier inside Redis. Every execution cycle begins from that location and moves forward only after anomaly cases have been committed successfully.

The concept sounds simple now, but it represented an important shift in how I thought about data processing. Instead of repeatedly solving the entire problem, the worker continuously continued from where it had previously stopped.

### Reconstructing Machine State

One of the more interesting challenges came from a design decision made much earlier in the project.

Telemetry is stored using a narrow EAV-style schema. A single physical observation becomes multiple independent sensor records. This approach provides flexibility at the ingestion layer because new sensor types can be added without changing the database structure.

The machine-learning pipeline, however, does not reason about individual sensor events.

It reasons about machine state.

Before anomaly detection could occur, those independent telemetry records had to be reconstructed into a synchronized analytical view representing the conveyor system at a specific point in time.

As a result, a significant portion of the scoring pipeline became feature engineering rather than model execution. Historical windows had to be assembled, rolling statistics calculated, and sensor readings aligned before the model could make a meaningful prediction.

One of the more surprising outcomes of the phase was realizing how little of the overall system was actually machine learning. Considerably more effort went into reconstructing context, managing processing state, and coordinating infrastructure than into training or executing the model itself.

### When the Worker Finally Came Alive

Getting the worker to execute once was relatively straightforward.

Getting it to operate continuously was much harder.

There were issues involving database sessions, Redis connectivity, duplicate anomaly creation, watermark synchronization, feature generation, and Docker networking. For a while, it felt like every problem solved revealed another problem hiding underneath it.

Eventually, the logs started showing something different.

```text
Rows evaluated = 383
Anomalies detected = 10
```

Followed shortly by:

```text
Cold-path run complete.
Watermark advanced.
```

Those messages were surprisingly satisfying.

For the first time, telemetry was flowing through the complete platform.

Events entered through the ingestion API.

The worker discovered them.

The feature pipeline transformed them.

The model evaluated them.

Anomaly cases appeared automatically.

The architecture diagrams were no longer describing a future system. They were describing a system that actually existed.

### Looking Back

At the start of this phase, I thought I was building a scoring pipeline.

Looking back, the scoring pipeline was only a small part of the work.

Most of the effort went into deciding where analytical processing should occur, how historical context should be reconstructed, how processing state should be tracked, and how machine-learning workloads could coexist with operational workloads without interfering with one another.

The anomaly detector remained the visible outcome, but the larger lesson was architectural.

By the end of the phase, the platform had moved beyond simple ingestion and storage. Telemetry could now enter the system continuously, be processed asynchronously, and generate investigation cases without human intervention.

The model may be responsible for identifying anomalies, but Phase 2.2 was where the platform learned how to think about incoming telemetry as an evolving system rather than a collection of isolated sensor readings.
