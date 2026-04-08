.PHONY: all test mypy test_verbose

all: test mypy

test:
	pytest tests/

mypy:
	mypy src/docs_buddy/ tests/

test_verbose:
	pytest -s tests/
