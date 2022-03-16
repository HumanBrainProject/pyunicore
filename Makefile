TESTS = $(wildcard tests/test_*.py)
export PYTHONPATH := pyunicore:tests
PYTHON=python3

test: runtest

.PHONY: runtest $(TESTS)

runtest: $(TESTS)

$(TESTS):
	@echo "\n** Running test $@"
	@${PYTHON} $@

clean:
	@find -name "*~" -delete
	@find -name "*.pyc" -delete
	@find -name "__pycache__" -delete
