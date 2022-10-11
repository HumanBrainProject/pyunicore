LINE_LENGTH=80
SOURCE_DIR=pyunicore/helpers
TEST_DIR=tests/helpers

black --line-length ${LINE_LENGTH} ${SOURCE_DIR} ${TEST_DIR}

reorder-python-imports --application-directories ${SOURCE_DIR}
reorder-python-imports --application-directories ${TEST_DIR}

flake8 \
  --max-line-length ${LINE_LENGTH} \
  --per-file-ignores="__init__.py:F401" \
  ${SOURCE_DIR} ${TEST_DIR}

