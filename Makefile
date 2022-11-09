TESTS = tests/unit
INTEGRATIONTESTS = $(wildcard tests/integration/test_*.py)
export PYTHONPATH := .
PYTHON = python3
PYTEST = pytest

test: runtest

integration-test: runintegrationtest

.PHONY: runtest $(TESTS) runintegrationtest $(INTEGRATIONTESTS)

runtest: $(TESTS)

$(TESTS):
	@echo "\n** Running test $@"
	@${PYTEST} $@

runintegrationtest: $(INTEGRATIONTESTS)

$(INTEGRATIONTESTS):
	@echo "\n** Running integration test $@"
	@${PYTHON} $@

clean:
	@find -name "*~" -delete
	@find -name "*.pyc" -delete
	@find -name "__pycache__" -delete
	@rm -rf build/
