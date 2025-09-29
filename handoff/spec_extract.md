# Spec Extract: Tysightv4 V2


## Architecture
The application is a multi-tool AI agent built with LangChain. It has two reasoning paths: a "Specialist" path for complex analytical questions (e.g., YoY performance) and a "Generalist" path for simple, ad-hoc queries.


## Controlled Vocabularies


### Intent Schema
`sales_performance`, `yoy_performance`, `distribution_summary`, `pricing_summary`, `velocity_summary`, `promotion_summary`, `direct_sql_query`


### Column `type` Vocabulary
`product_attribute`, `location_attribute`, `mod_attribute`, `market_or_store`, `time_abs`, `time_agg`, `pos_measure`, `mod_measure`, `location_measure`, `media_measure`


## Critical SQL Rules
All generated SQL must use `canonical_name`s, build a `WHERE` clause from UI filters, use `LOWER()` for case-insensitivity, and include a `LIMIT 1000` for safety.
