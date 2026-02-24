.PHONY: all test mypy

all:	test mypy

test:
	pytest --doctest-modules *.py

mypy:
	mypy *.py
