# V3 Project Roadmap

This document outlines the prioritized features for the V3 development phase of the Tysightv4 application.

## 1. Graphing & Charting Capability
- **Objective**: Enhance the "Ask & Analyze" page to visualize the results of SQL queries.
- **Implementation**:
    - Add a new "Chart Generation" tool to the V2 agent.
    - After a data table is generated, the agent will determine the most appropriate chart type (e.g., bar, line, pie).
    - The agent will generate the chart and display it below the data table in the UI.


## 2. Advanced HTML Reports
- **Objective**: Implement the "Download Report" feature.
- **Implementation**:
    - Create a new "Report Generation" tool.
    - This tool will take the summary text, the data table, and the newly generated chart.
    - It will bundle all three components into a single, self-contained HTML file that the user can download.


## 3. Data Harmonization & Joins
- **Objective**: Evolve the application to support queries across multiple, related datasets.
- **Implementation**:
    - Design and implement a central "Data Dictionary" for managing globally unique `canonical_name`s.
    - Update the "Create Kind" UI to allow users to map their columns to this central dictionary.
    - Upgrade the SQL generation agent to be able to construct queries with `JOIN` clauses based on these harmonized columns.
