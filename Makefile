# Makefile for ansible_dynamic_inventory_plugin
# https://www.gnu.org/software/make/manual/make.html
SHELL := /bin/sh
VENV = venv
VENV_BIN = ./$(VENV)/bin

install: ci-requirements.txt ## Install the application requirements
	@echo "- - - - - - - - INSTALL - - - - - - - -"
	# Use `python3` from the current environment to create a virtual environment
	python3 -m venv $(VENV)
	# Upgrade PIP in the virtual environment
	$(VENV_BIN)/python -m pip install --upgrade pip
	# Install CI components in the virtual environment
	$(VENV_BIN)/python -m pip install -r ci-requirements.txt

format: ## (Re)Format the application files
	$(VENV_BIN)/black *.py

lint: ## Lint the application files
	$(VENV_BIN)/ruff check

test: ## Test the the application files
	$(VENV_BIN)/python -m pytest -v *.py

all: install format lint test

# Actions that don't require target files
.PHONY: clean
.PHONY: help

help: ## Print a list of make options available
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' ${MAKEFILE_LIST} | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

clean: ## Clean up files used locally when needed
	# Remove the Python cache files
	rm -rf ./__pycache__
	# Remove the Python the virtual environment
	rm -rf ./$(VENV)