TESTS = $(wildcard tests/test_*.py)
INTEGRATIONTESTS = $(wildcard integration-tests/test_*.py)
export PYTHONPATH := pyunicore
PYTHON=python3

test: runtest

integration-test: runintegrationtest

.PHONY: runtest $(TESTS) runintegrationtest $(INTEGRATIONTESTS)

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
