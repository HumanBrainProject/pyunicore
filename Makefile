TESTS = $(wildcard tests/test_*.py)
INTEGRATIONTESTS = $(wildcard integration-tests/test_*.py)
export PYTHONPATH := .
PYTHON=python3

# Currently only lint the helpers package to avoid merge conflicts.
LINE_LENGTH = 80
HELPERS_SOURCE_DIR = pyunicore/helpers
HELPERS_TEST_DIR = tests/helpers

test: runtest

integration-test: runintegrationtest

.PHONY: runtest $(TESTS) runintegrationtest $(INTEGRATIONTESTS)

lint:
	black --line-length $(LINE_LENGTH) $(HELPERS_SOURCE_DIR) $(HELPERS_TEST_DIR)
	reorder-python-imports --application-directories $(HELPERS_SOURCE_DIR)
	reorder-python-imports --application-directories $(HELPERS_TEST_DIR)
	flake8 $(HELPERS_SOURCE_DIR) $(HELPERS_TEST_DIR)

test-helpers:
	pytest --cov=$(HELPERS_SOURCE_DIR) --cov-report term-missing $(HELPERS_TEST_DIR)

runtest: $(TESTS)

$(TESTS):
	@echo "\n** Running test $@"
	@${PYTHON} $@

runintegrationtest: $(INTEGRATIONTESTS)

$(INTEGRATIONTESTS):
	@echo "\n** Running integration test $@"
	@${PYTHON} $@

clean:
	@find -name "*~" -delete
	@find -name "*.pyc" -delete
	@find -name "__pycache__" -delete
	@rm -rf build/
