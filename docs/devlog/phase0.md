# Phase 0 Setup: Building the Foundation Before the ML

When I started this project, I thought the interesting part would be anomaly detection models and AI agents. After finishing Phase 0, I realized most of the work was actually about building a reliable foundation. Before any model can predict failures, the system needs a way to generate data, store it, validate it, test it, and run consistently across different environments.

## Why I Split Telemetry and Investigation Data

One of the first design decisions was separating raw sensor readings from investigation cases. Initially, I considered keeping everything in one place because it felt simpler. The more I thought about it, the more it felt like two different types of data. Sensor readings are facts. Once a reading is generated, it should never change. Investigation cases are different because their status changes over time. A case can be flagged, investigated, and eventually resolved. Splitting these tables made the design easier to reason about and helped me understand why many systems separate immutable events from mutable business state.

## Why Evidence Became Append-Only

The idea of an append-only evidence table came from thinking about how investigations actually work. If an anomaly is detected, I might initially have one piece of supporting evidence and later discover two more. Deleting or overwriting earlier evidence felt wrong because it destroys the history of how the conclusion was reached. By making evidence append-only, the system keeps a trail of observations instead of only storing the final answer. It also makes future extensions easier because new evidence types can simply be added without changing existing records.

## Understanding the Wide-to-Narrow Transformation

This was probably the most confusing design decision at first. The synthetic hardware generator naturally produces rows that look like real sensor packets:

```text
timestamp | torque | speed | fill_level
```

My first instinct was to store the data exactly like that. While working through the schema design, I realized that adding a new sensor later would require changing the database structure. The narrow format avoids that problem because sensors become data instead of columns. The trade-off is that one hardware packet turns into multiple database rows. Once I implemented the transformation in `seed_db.py`, the reasoning finally clicked for me.

## What Docker Compose Actually Taught Me

Before this project, Docker felt like a complicated packaging tool. I could follow tutorials, but I didn't really understand why things were configured the way they were. The biggest lesson came from figuring out how FastAPI, PostgreSQL, and Redis communicate. I originally assumed Docker somehow made everything automatically discoverable. After spending time with Docker Compose, I realized that Compose creates the network, but my application still needs to know where services are located. The way I think about it now is that Docker creates the roads, while environment variables tell the application which address to drive to.

## What I Learned From GitHub Actions

I started Phase 0 thinking CI was mostly about running tests automatically. Setting up GitHub Actions changed that understanding. Every workflow starts from a completely fresh machine. If the pipeline succeeds, it means the project can rebuild itself from scratch without relying on anything stored on my laptop. That made me think differently about project setup. The workflow became a way to verify that the repository contains everything needed to reproduce the environment.

## What Would Break If Sensors Started Sending Duplicate Events?

My first answer would have been database performance. After thinking through the design, I realized the bigger problem is data quality. Right now, the system assumes every incoming event is legitimate. If the same reading is accidentally sent multiple times, those duplicates would influence averages, rolling metrics, and eventually anomaly detection results. The database can store duplicates without complaint, but the insights produced from that data would become less trustworthy. That made me realize that scaling a system isn't only about handling more traffic. Sometimes it's about making sure the data remains correct as volume increases.

## Looking Back

The most valuable part of Phase 0 wasn't Docker, PostgreSQL, Redis, or GitHub Actions individually. It was understanding how they fit together. Before starting, these tools felt like separate technologies that appeared in job descriptions. After building the project, I started seeing them as parts of the same system: data generation, storage, networking, validation, and automation. The anomaly detection models will come later, but Phase 0 gave me a much better understanding of the infrastructure those models will depend on.
