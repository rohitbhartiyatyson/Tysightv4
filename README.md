# Tysightv4

Tysightv4 is a modular Streamlit application for answering natural language questions about single datasets using a robust, multi-tool AI agent.

## Prerequisites
* Python 3.11+
* Poetry
* Make


## Installation
1. Clone the repository:
   `git clone <repository_url>`
2. Navigate to the project directory:
   `cd Tysightv4`
3. Install dependencies using the Makefile:
   `make install`


## Configuration
1. Copy the example environment file:
   `cp .env.example .env`
2. Edit the `.env` file and add your LLM provider's API key and base URL.


## How to Run
`streamlit run app/Home.py`


## How to Test
`make smoke-test`
