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
