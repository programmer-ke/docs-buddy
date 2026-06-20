.PHONY: all test mypy test_verbose black_check

all: test mypy black_check

test:
	pytest tests/

mypy:
	mypy src/docs_buddy/ tests/

test_verbose:
	pytest -s tests/

black_check:
	black --check .
