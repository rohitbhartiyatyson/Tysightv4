import os
from insight_agent.prompt_builder import build_prompt
from insight_agent.llm_client import get_sql_from_prompt

# --- Inputs that would come from the UI ---
kind_name = "NIQ POS"
user_question = "what is total dollar sales for the bacon category"
selected_filters = {"market": "Total US Food"} # Example filter

print("--- Running Backend Test ---")
# 1. Build the prompt
prompt = build_prompt(kind_name, user_question, selected_filters)
print('\n--- Generated Prompt (first 100 chars): ---\n' + prompt[:100] + '...')
# 2. Get SQL from LLM
sql = get_sql_from_prompt(prompt)
print('\n--- Received SQL from LLM: ---\n' + sql)
print('\n--- Test Complete ---')
