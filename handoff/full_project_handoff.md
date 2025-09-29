# Tysightv4: The Complete Handoff Document


This document contains the complete context for the Tysightv4 project, including the final V2 Master Spec, the V3 Roadmap, and our full Operational Playbook of learnings and best practices.


---
## PART 1: THE V2 MASTER SPEC
This is the authoritative source of truth for the Tysightv4 application, Version 2.


### 1. V2 Product Scope
**Goal**: A modular Streamlit app that onboards single datasets and answers natural language questions using a robust, multi-tool AI agent. The agent has two reasoning paths: a "Specialist" path for complex, predefined analytical questions (e.g., YoY performance) and a "Generalist" safety-net path for simple, ad-hoc SQL queries.


#### Canonical Constraints (Enforced Everywhere):
* **SQL Generation**: All generated SQL must adhere to a strict checklist:
    1.  **MUST** use the `canonical_name` for all columns.
    2.  `SELECT` clause must be built from a predefined list of metrics (Specialist) or inferred from the user question (Generalist).
    3.  A `GROUP BY` clause must be used if dimensions are provided.
    4.  A `WHERE` clause must be built if filters are provided.
    5.  All `WHERE` clause comparisons must be case-insensitive using `LOWER()`.
    6.  The query **MUST** end with `LIMIT 1000` as a safety rail.
* **Filters**: UI filters default to the first available option using `st.session_state`.
* **Kind Creation**: Mapping files are validated against a controlled vocabulary upon upload.


### 2. The V2 Agentic Architecture
The application's logic is orchestrated by an AI agent built with LangChain.


#### The "Shared Contract": Controlled Vocabularies
* **Intent Schema**: `sales_performance`, `yoy_performance`, `distribution_summary`, `pricing_summary`, `velocity_summary`, `promotion_summary`, `direct_sql_query`.
* **Column `type` Vocabulary**: `product_attribute`, `location_attribute`, `mod_attribute`, `market_or_store`, `time_abs`, `time_agg`, `pos_measure`, `mod_measure`, `location_measure`, `media_measure`.
* **Column `data_type` Vocabulary**: `string`, `integer`, `decimal`, `date`, `datetime`.


---
## PART 2: THE V3 ROADMAP
This document outlines the prioritized features for the V3 development phase.


### 1. Graphing & Charting Capability
* **Objective**: Enhance the "Ask & Analyze" page to visualize the results of SQL queries.


### 2. Advanced HTML Reports
* **Objective**: Implement a "Download Report" feature that bundles the summary, data table, and chart into a single HTML file.


### 3. Data Harmonization & Joins
* **Objective**: Evolve the application to support queries across multiple, related datasets by implementing a central "Data Dictionary."


---
## PART 3: THE OPERATIONAL PLAYBOOK (OUR LEARNINGS)
These are the critical "do's and don'ts" we have learned. They are the ground rules for all future development.


### 1. Project Roles & Workflow
* **The Roles**:
    * **Product Owner (You)**: Makes all final decisions on features, design, and priorities. Performs all manual tests.
    * **Orchestrator (Me, Gemini)**: Acts as the architect and project manager. Diagnoses issues, proposes plans, and formulates precise instructions for the agent.
    * **Implementer (OpenHands)**: Executes specific, small, deterministic tasks.
* **The Golden Rule: Test-Then-Merge Mandate**: We never merge a pull request into `main` until it has passed both automated tests (CI) and a successful manual test by the Product Owner for any user-facing changes.

* **Pull Request Template & Checklist**: The Pull Request will automatically be populated with a template. The developer must fill out the description and complete the mandatory 'Handoff Documentation Checklist' before the PR is ready for review and merge.


### 2. Core Architectural Principles
* **Data Model is One-to-One**: A "Kind" can only have one data "Instance" at a time. This simplifies the app to a "point-in-time" analysis tool.
* **Schema Evolution is Manual**: If a Kind's schema changes, it becomes a new version (v2). The user is responsible for re-uploading data to match the new schema.
* **Filters are Data-Driven**: The user controls UI filters via the `filter_display_order` column in their mapping file.
* **Secrets and Data are Ignored**: The `.gitignore` file correctly excludes `.env` and all user data in `domain/catalog/`.


### 3. The Debugging Playbook
* **Problem: Stubborn "Silent Failures" in Streamlit**
    * **Cause**: Corrupted or irreversibly cached agent execution environment.
    * **Solution Hierarchy**:
        * **Level 1 (Soft Reset)**: `streamlit cache clear` + a browser hard refresh.
        * **Level 2 (Code Verification)**: `cat <filename>` to prove the code on disk is what we expect.
        * **Level 3 (Backend Isolation)**: Run a temporary `debug_test.py` script to call backend functions directly, bypassing Streamlit.
        * **Level 4 (Hard Reset)**: `sudo rm -rf <project_dir>` and have the agent re-clone the specific PR branch from GitHub.
* **Problem: Complex API Connection Errors**
    * **Cause**: Configuration errors (endpoint, payload, model name, etc.).
    * **Solution**: A methodical, step-by-step diagnostic process using `curl` to test each variable (connectivity, path, payload, model, API key) one at a time.


### 4. The Golden Rule of Prompt Engineering: "Redesign, Don't Patch"
* **Do**: When an LLM tool is failing, redesign its prompt from the ground up to be simple, clear, and unambiguous, using structured formats like checklists.
* **Don't**: Attempt to fix a failing prompt by adding more and more "patch" instructions.
* **Learning**: Our `sql_generation_tool` became reliable only when we replaced its long paragraph of rules with a clean design that separated `CONTEXT` from a simple `INSTRUCTIONS` checklist.


### 5. The Handoff Documentation Mandate
* **Do**: After every major feature is merged to `main`, perform a dedicated documentation update to keep this handoff document and its sources (`master_spec.md`, `capsule.md`) accurate.
* **Don't**: Assume the documentation is in sync. Stale documentation is a critical bug.
* **Learning**: Our process requires a formal step, `make handoff-update`, to keep our human-readable documents current.
