# Master Spec: Tysightv4 V2
This document is the authoritative source of truth for the Tysightv4 application, Version 2.


## 0. Output protocol
When you relay any OpenHands result to me, start the message with exactly:
Below is the OpenHands Output:
At the end of every OpenHands task, the agent must print three things in full:
handoff/capsule.md
handoff/status.json
A RUN RECEIPT block, fully populated.


## 1. V2 Product Scope
**Goal**: A modular Streamlit app that onboards single datasets and answers natural language questions using a robust, multi-tool AI agent. The agent has two reasoning paths: a "Specialist" path for complex, predefined analytical questions (e.g., YoY performance) and a "Generalist" safety-net path for simple, ad-hoc SQL queries.


### Canonical Constraints (Enforced Everywhere):
* **NL Prompt**: Selected Kind only, present columns only, ≤ 2 micro-examples.
* **SQL Generation**: All generated SQL must adhere to a strict checklist:
    1.  **MUST** use the `canonical_name` for all columns.
    2.  `SELECT` clause must be built from a predefined list of metrics (Specialist) or inferred from the user question (Generalist).
    3.  A `GROUP BY` clause must be used if dimensions are provided.
    4.  A `WHERE` clause must be built if filters are provided.
    5.  All `WHERE` clause comparisons must be case-insensitive using `LOWER()`.
    6.  The query **MUST** end with `LIMIT 1000` as a safety rail.
* **Filters**: UI filters default to the first available option using `st.session_state`.
* **Kind Creation**: Onboarding a new Kind only auto-fills `format_hint` and `unit` from the sample data. No other autofill is permitted. The mapping file is validated against a controlled vocabulary upon upload.


### Terminology & Layout
* `insight_agent/`, `tools/`, `handoff/`, `domain/catalog/{kinds,datasets}/`, `runs/`, `logs/`.
* **Kind**: A dataset type, versioned under `domain/catalog/kinds/<kind_name>/vN/`.
* **Instance**: A concrete uploaded file, under `domain/catalog/datasets/<kind_name>/<instance_id>/`.


### Handoff Docs
* `handoff/status.json`: Machine state.
* `handoff/capsule.md`: High-level summary.
* `handoff/master_spec.md`: This document.
* `handoff/spec_extract.md`: A 2–4 page digest of this master spec.
* `handoff/new_chat_bundle.md`: The file to copy-paste into a new chat session.


### Data Contracts (User-Provided)
* **Required Mapping Workbook**: `original_name`, `canonical_name`, `type`, `description`, `data_type`, optional `is_additive`, optional `filter_display_order`.
* **Mandatory Sample Data**: Used strictly for validation and to populate hints.


### The V2 Agentic Architecture
The application's logic is orchestrated by an AI agent built with LangChain, following a "Hybrid Agentic Workflow."


#### The "Shared Contract": Controlled Vocabularies
* **Intent Schema**: `sales_performance`, `yoy_performance`, `distribution_summary`, `pricing_summary`, `velocity_summary`, `promotion_summary`, `direct_sql_query`.
* **Column `type` Vocabulary**: `product_attribute`, `location_attribute`, `mod_attribute`, `market_or_store`, `time_abs`, `time_agg`, `pos_measure`, `mod_measure`, `location_measure`, `media_measure`.
* **Column `data_type` Vocabulary**: `string`, `integer`, `decimal`, `date`, `datetime`.


#### The Toolbox
The agent has access to four specialized tools:
1.  **`intent_recognition_tool` (LLM-based)**: Classifies the user's question into an `IntentSchema` intent and extracts entities and dimensions.
2.  **`metric_selection_tool` (Code-based)**: Takes a "Specialist" intent and deterministically returns the required list of `canonical_name`s.
3.  **`sql_generation_tool` (LLM-based)**: Receives context (schema, filters) and instructions (metrics, dimensions) and generates a compliant SQL query using one of two specialized prompts.
4.  **`data_synthesis_tool` (LLM-based)**: Takes the final data table and generates a narrative summary.


#### The Reasoning Paths
1.  **Triage**: The `intent_recognition_tool` assesses the user's question.
2.  **Specialist Path**: For known analytical intents, the agent follows the full chain: `Intent -> Metrics -> SQL -> Data -> Summary`.
3.  **Generalist Path**: For simple, ad-hoc intents (`direct_sql_query`), the agent bypasses the metric selection step: `Intent -> SQL -> Data -> Summary`.


## 2. OpenHands operating model (rails you enforce every time)
* **Run Contract**: 1 command per call, single line; no heredocs; no multi-line; no subshells ($(), backticks); no inline comments in the command string.
* **File Edits**: Atomic Python writes only for file edits (e.g., Path(...).write_text(...)).
* **GitHub API**: All GitHub API calls use a tiny Python helper at scripts/oh_gh.py.
* **Testing**: `make install` → `TEST_MODE=1 smoke` → `TEST_MODE=1 e2e` → `make handoff-update`.
* **Merge Policy**: Merge only when both CI checks are green on the PR head SHA.
* **Conflict Policy**: `handoff/**` → ours. `.github/workflows/**` → main. `requirements.txt` → union. Any other conflicts → stop and report.


## 4. CI, tokens, and permissions
* **CI Shape**: Two jobs: `smoke` (fast) → `e2e` (depends on smoke). Both run with `TEST_MODE=1`. Both always upload `handoff/**`, `runs/**`, `logs/**` as fail-soft artifacts.
* **Permissions**: `actions: write`, `contents: read`. `workflows: write` if needed.
* **Tokens**: From environment variables only. Never stored.


## 5. Merge & conflict policy (deterministic)
* When to merge: Only after both smoke and e2e are successful on the PR head.
* If `mergeable_state` is `dirty`: Resolve only `handoff/**` (ours), `.github/workflows/**` (main), and `requirements.txt` (union). All other files → stop & report.


## 6. Stuck detection, diagnostics & recovery
* Any step silent >60s = stalled. Abort and report.
* Standard diagnostics task: save logs, save conflicted files list, update `status.json`.


## 7. Server discipline (no blocking servers)
* No foreground servers. Streamlit must run in the background.
* Status checks must use one-shot `tail`, not `tail -f`.


## 8. Determinism & idempotency
* All steps must be safe to re-run. `TEST_MODE=1` must force deterministic behavior.


## 9. How you (Gemini) will orchestrate
* Ensure the microagent is triggered.
* Provide tiny, code-free task blocks.
* Enforce the output protocol (prefix + Run Receipt).
* Parse handoff files and Run Receipt; propose the next smallest task.


## 10. The V3+ Roadmap (Intentionally Postponed Features)
* **Graphing Capability**: Visualize the results of SQL queries directly in the UI.
* **Advanced HTML Reports**: An enhanced "Download Report" feature that bundles the summary, data table, and future graphs into a single, portable HTML file.
* **Data Harmonization & Joins**: Introduce a central data dictionary to manage globally unique `canonical_name`s, enabling joins and comparisons across different Kinds.
* **Interactive Mapping Editor**: A UI-driven tool for creating and editing Kind mappings, replacing the need for manual CSV/Excel file editing.
* **Backward Compatibility for Mappings**: A normalization layer to automatically convert legacy mapping files to the new V2 standard.
Commit the new file with the message: docs: Create definitive V2 master spec.
