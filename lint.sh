LINE_LENGTH=88
SOURCE_DIR=pyunicore/model
TEST_DIR=tests/model

black --line-length ${LINE_LENGTH} ${SOURCE_DIR} ${TEST_DIR}

reorder-python-imports --application-directories ${SOURCE_DIR}
reorder-python-imports --application-directories ${TEST_DIR}

flake8 --max-line-length ${LINE_LENGTH} ${SOURCE_DIR} ${TEST_DIR}

