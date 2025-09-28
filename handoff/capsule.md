Objective: Add a user-visible warning when a selected Kind has no defined filters.

Implemented: Added a conditional check in app/pages/3_Ask_and_Analyze.py that inspects the loaded profile for any filter_display_order values. If none are present, the UI displays an informational message guiding users to add filter_display_order in their mapping file.

Files changed:
- app/pages/3_Ask_and_Analyze.py (added filters_defined check and st.info warning)

Commit: feat: Add no-filters-found warning
Branch: feat/no-filters-warning

How to reproduce locally:
1. Checkout the branch feat/no-filters-warning
2. Start the Streamlit app (e.g., streamlit run app/pages/3_Ask_and_Analyze.py)
3. Select a Kind whose mapping/profile lacks filter_display_order keys
4. Observe the info message near filters area

Status: smoke tests failed due to missing pytest in the environment when running make smoke-test. No changes were made beyond the single UI edit.
