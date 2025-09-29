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


#### The Reasoning Paths
1.  **Specialist Path**: For known analytical intents, the agent follows the full chain: `Intent -> Metrics -> SQL -> Data -> Summary`.
2.  **Generalist Path**: For simple, ad-hoc intents (`direct_sql_query`), the agent bypasses the metric selection step: `Intent -> SQL -> Data -> Summary`.

---
## PART 2: THE V3 ROADMAP
This document outlines the prioritized features for the V3 development phase.


### 1. Graphing & Charting Capability
* **Objective**: Enhance the "Ask & Analyze" page to visualize the results of SQL queries.
* **Implementation**: Add a new "Chart Generation" tool to the agent that automatically determines the best chart type and generates a visualization.


### 2. Advanced HTML Reports
* **Objective**: Implement a "Download Report" feature.
* **Implementation**: Create a tool that bundles the summary text, the data table, and the new chart into a single, downloadable HTML file.


### 3. Data Harmonization & Joins
* **Objective**: Evolve the application to support queries across multiple, related datasets.
* **Implementation**: Design and implement a central "Data Dictionary" for managing globally unique `canonical_name`s to enable `JOIN`s.

---
## PART 3: THE OPERATIONAL PLAYBOOK (OUR LEARNINGS)
These are the critical "do's and don'ts" we have learned. They are the ground rules for all future development.


### 1. The Golden Rule: Test-Driven Development and Granular Steps
* **Do**: Break every feature down into the smallest possible, verifiable steps.
* **Don't**: Attempt to build and test multiple new components at once.
* **Learning**: Our biggest failures came from trying to build the entire agent chain in one go. We became successful when we adopted a test-driven approach, writing specific unit tests for each new tool (`intent`, `metric`, `sql`) before integrating them. **Every new tool must have a unit test before it is used in the main agent chain.**


### 2. The Rule of the "Shared Contract"
* **Do**: Define a strict, explicit "Shared Contract" (like our `IntentSchema`) that governs the inputs and outputs between different agent tools.
* **Don't**: Allow one tool to pass a "creative" or unconstrained output to another tool.
* **Learning**: The agent consistently failed when the `intent_recognition_tool` could invent its own intents. It became reliable only after we forced it to choose from a predefined list that the `metric_selection_tool` was guaranteed to understand.


### 3. The Golden Rule of Prompt Engineering: "Redesign, Don't Patch"
* **Do**: When an LLM tool is failing, redesign its prompt from the ground up to be simple, clear, and unambiguous. Use structured formats like checklists.
* **Don't**: Attempt to fix a failing prompt by adding more and more "patch" instructions.
* **Learning**: Our `sql_generation_tool` failed repeatedly as we kept adding "CRITICAL RULE" patches to a confusing paragraph. It became reliable only when we replaced the entire prompt with a clean, structured design that separated `CONTEXT` from a simple `INSTRUCTIONS` checklist.


### 4. Our Debugging Hierarchy for UI and Agent Failures
* **Do**: Follow a methodical process to diagnose bugs, starting with the simplest cause.
* **Level 1 (UI Glitches)**: Suspect a Streamlit `rerun` issue. Use `st.session_state` to ensure values persist correctly.
* **Level 2 (Silent Failures)**: Suspect a broken agent chain. Use the "Evidence UI" to find the first tool that produced an incorrect or empty output.
* **Level 3 (Tool Failures)**: Suspect a bad prompt or faulty logic. Add direct `print()` statements to the tool to see the exact inputs it received and the raw outputs it produced.
* **Level 4 (Test Failures)**: Suspect an environment issue. Delete `__pycache__` directories or check for duplicate project folders.


### 5. Mandatory Workflow Rules
* **Do**: Run `make smoke-test` after every single code change.
* **Do**: Run servers in the background (`nohup ... &`) to prevent the agent from hanging.
* **Do**: Ensure all handoff documents (`master_spec.md`, `new_chat_bundle.md`) are updated at the end of every major feature merge.


### 6. The Handoff Documentation Mandate
* **Do**: After every major feature is merged into `main`, perform a dedicated documentation update to keep this handoff document and its sources (`master_spec.md`, `capsule.md`) accurate.
* **Don't**: Assume the documentation is in sync. Stale documentation is a critical bug.
* **Learning**: Our process requires a formal step to update our human-readable documents, not just our code. We will create a `make handoff-update` command to remind us of this crucial final step in our workflow. **This document must always be a living document.**
