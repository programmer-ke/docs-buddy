.PHONY: all test mypy

all: test mypy

test:
	pytest tests/

mypy:
	mypy src/docs_buddy/ tests/
