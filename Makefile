.PHONY: help install clean docs test ci mypy pyright pyupgrade stubs codecs ruff release example-ci

help: 
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  install    to install the package"
	@echo "  clean      to clean the directory tree"
	@echo "  docs       to generate the documentation"
	@echo "  ci 	    to run the CI workflows"
	@echo "  mypy       to run the mypy static type checker"
	@echo "  pyright    to run the pyright static type checker"
	@echo "  stubs      to generate the type stubs"
	@echo "  codecs     to parse and generate the fourcc class"
	@echo "  pyupgrade  to run pyupgrade"
	@echo "  ruff 	    to run ruff"
	@echo "  test       to run the tests"
	@echo "  release    to perform all actions required for a release"
	@echo "  example-ci to run the CI workflows for the example scripts"

install:
	pip3 install .

clean: 
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf jetsontools/*.egg-info
	rm -rf src/jetsontools/*.egg-info
	pyclean .
	rm -rf .mypy_cache
	rm -rf .ruff_cache

docs:
	python3 ci/build_example_docs.py
	rm -rf docs/source/*
	sphinx-apidoc -o docs/source/ src/jetsontools/
	cd docs && make html

stubs:
	python3 ci/make_stubs.py

codecs:
	python3 scripts/parse_codec.py --file=data/codecs.html --output=src/jetsontools/io/_fourcc.py

ci: ruff mypy

mypy:
	python3 -m mypy src/jetsontools --config-file=pyproject.toml

pyright:
	python3 -m pyright --project=pyproject.toml

ruff:
	python3 -m ruff format ./src/jetsontools
	python3 -m ruff check ./src/jetsontools --fix --preview

test:
	./ci/run_tests.sh

example-ci: pyupgrade
	python3 -m ruff format ./examples
	python3 -m ruff check ./examples --fix --preview --ignore=T201,INP001,F841

release: clean install ci test docs example-ci
