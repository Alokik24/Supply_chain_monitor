# Phase 1: Understanding the Data Before Training the Models

When I finished building the synthetic telemetry generator, my instinct was to move directly into anomaly detection models. After all, that was the original goal of the project. The more I thought about it, the more uncomfortable that felt.

I had generated thousands of rows of telemetry, but I didn't actually understand the data yet.

Before training any model, I wanted to answer a simpler question:

> If I looked at the sensor readings myself, could I tell when something was going wrong?

That became the starting point for Phase 1.

---

## What the EDA Revealed

I began by exploring the generated telemetry and comparing normal operating periods against the injected anomaly windows.

Initially, I expected the anomalies to stand out clearly. Since I had created the simulation myself, I assumed the failures would be obvious.

The reality was more interesting.

Some anomaly periods were easy to spot. Others blended into the natural variation of the manufacturing process much more than I expected. A torque spike might be visible in one situation and almost disappear in another. Fill-level behaviour was sometimes informative and sometimes not.

The biggest observation was that anomalies rarely appeared as isolated sensor problems.

When something went wrong, multiple sensors tended to react together.

A conveyor slowdown affected speed measurements, but it also influenced torque and fill-level behaviour. Looking at individual sensor values only told part of the story.

That realization changed the direction of the phase.

The problem was no longer:

> Can I detect anomalies?

Instead, it became:

> How do I represent machine behaviour in a way that makes anomalies easier to identify?

---

## Moving Beyond Raw Sensor Values

The EDA suggested that a single measurement was often less useful than its relationship to recent history.

A torque value of 170 might be completely normal in one operating condition and highly unusual in another.

The raw number alone didn't provide enough context.

I started experimenting with rolling statistics to capture how a sensor was behaving relative to its recent baseline.

This led to the feature engineering pipeline.

Instead of feeding models raw telemetry, I began constructing features such as:

* Rolling means
* Rolling standard deviations
* Z-scores
* Rate-of-change metrics
* Baseline deviation measures

What surprised me was how much clearer the anomaly patterns became once historical context was introduced.

The engineered features felt less like measurements and more like descriptions of system behaviour.

At that point, I started seeing feature engineering as more than a preprocessing step. It was becoming the bridge between raw telemetry and meaningful operational signals.

---

## A New Problem Appeared

Once the feature pipeline was working, another question surfaced.

If these engineered features were useful, how would they exist in a real system?

During offline analysis, generating them was easy. I already had access to the entire dataset.

A live system would be different.

A new telemetry event arrives.

The model needs rolling statistics.

Where do those statistics come from?

My first instinct was simple: query PostgreSQL whenever a prediction is needed and calculate everything on demand.

The idea worked on paper.

The more I thought about it, the less practical it seemed.

Every prediction would require additional database queries. As the telemetry volume increased, those analytical calculations would begin competing with ingestion workloads.

The system would spend more time rebuilding context than making decisions.

This was the first time I encountered the idea of a feature store.

I didn't implement one during Phase 1, but the concept immediately made sense. Instead of repeatedly recalculating historical features, the system could maintain them separately and serve them directly when needed.

That realization would eventually influence the architecture of later phases.

---

## Evaluating the Models

With the feature engineering pipeline in place, I finally turned my attention to model validation.

At first, I was focused on model selection.

Should I use Isolation Forest?

Would Random Forest perform better?

Would another anomaly detection algorithm be more appropriate?

The more I read, the more I realized I was asking the wrong question.

Before comparing models, I needed confidence that the evaluation process itself was trustworthy.

Time-series data introduces a unique problem: leakage.

It is surprisingly easy to accidentally allow future information to influence past predictions. Strong evaluation metrics become meaningless if the testing process is flawed.

As a result, I spent more time thinking about validation than algorithms.

I established a chronological train-test split and carefully separated feature generation between the training and testing periods.

Only after that did I begin evaluating models.

I chose two approaches.

Isolation Forest served as an unsupervised baseline because real manufacturing environments often have very limited labeled failure data.

Random Forest provided a supervised comparison using the anomaly labels available in the synthetic dataset.

The results were encouraging, but they weren't the most important outcome of the phase.

What mattered more was gaining confidence that the engineered features were capturing meaningful signals and that the evaluation process was defensible.

---

## Looking Back

At the beginning of Phase 1, I viewed anomaly detection primarily as a modelling problem.

By the end of the phase, I had a very different perspective.

The models were important, but they sat on top of several layers of work:

* Understanding the data
* Creating meaningful features
* Designing a reliable evaluation process
* Thinking about how features would eventually be served in real time

The biggest lesson was that machine learning systems are rarely limited by algorithms alone.

The quality of the data representation often matters just as much as the model consuming it.

Phase 1 started with a dataset and ended with a much clearer understanding of what the rest of the system would need to become.
