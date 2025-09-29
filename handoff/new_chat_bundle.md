# Project Capsule: Tysightv4 V2


## Objective
Build a modular Streamlit app that onboards data and answers natural language questions using a robust, multi-tool AI agent.


## Current State (V2 Complete)
The application is feature-complete for V2. The `main` branch contains a stable, intelligent agent built with LangChain. The agent uses two distinct reasoning paths:
1.  A "Specialist" path for complex, predefined analytical questions (e.g., YoY performance).
2.  A "Generalist" safety-net path for simple, ad-hoc SQL queries.


All major V1 and V2 features are merged into `main`. The application is ready for the next phase of development.


## Next Steps
Begin planning the V3 roadmap, which includes:
* Graphing and charting capabilities.
* Advanced HTML report downloads.
* Data harmonization for multi-dataset joins.


---
# Spec Extract: Tysightv4 V2


## Architecture
The application is a multi-tool AI agent built with LangChain. It has two reasoning paths: a "Specialist" path for complex analytical questions (e.g., YoY performance) and a "Generalist" path for simple, ad-hoc queries.


## Controlled Vocabularies


### Intent Schema
`sales_performance`, `yoy_performance`, `distribution_summary`, `pricing_summary`, `velocity_summary`, `promotion_summary`, `direct_sql_query`


### Column `type` Vocabulary
`product_attribute`, `location_attribute`, `mod_attribute`, `market_or_store`, `time_abs`, `time_agg`, `pos_measure`, `mod_measure`, `location_measure`, `media_measure`


### Column `data_type` Vocabulary
`string`, `integer`, `decimal`, `date`, `datetime`


## Critical SQL Rules
All generated SQL must use `canonical_name`s, build a `WHERE` clause from UI filters, use `LOWER()` for case-insensitivity, and include a `LIMIT 1000` for safety.
