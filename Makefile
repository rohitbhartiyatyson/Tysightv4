install:
	@echo "Installing package and test dependencies..."
	pip install -e .[test]

smoke-test:
	@echo "Running smoke tests..."
	pytest -q

e2e-test:
	@echo "e2e-test placeholder"

handoff-update:
	@echo "handoff-update placeholder"
