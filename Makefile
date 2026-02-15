PYTHON ?= python

.PHONY: pretest
pretest:
	@bash ./backend/scripts/dev/clean_pycache.sh

.PHONY: test-unit
test-unit: pretest
	@$(PYTHON) -m pytest -q backend/tests/unit

# Makefile for Forge project
SHELL=/usr/bin/env bash

# Variables
BACKEND_HOST ?= "127.0.0.1"
BACKEND_PORT ?= 3000
BACKEND_HOST_PORT = "$(BACKEND_HOST):$(BACKEND_PORT)"
DEFAULT_WORKSPACE_DIR = "./workspace"
DEFAULT_MODEL = "gpt-4o"
CONFIG_FILE = config.toml
PRE_COMMIT_CONFIG_PATH = "./backend/dev_config/python/.pre-commit-config.yaml"
PYTHON_VERSION = 3.12

# ANSI color codes
GREEN=$(shell tput -Txterm setaf 2)
YELLOW=$(shell tput -Txterm setaf 3)
RED=$(shell tput -Txterm setaf 1)
BLUE=$(shell tput -Txterm setaf 6)
RESET=$(shell tput -Txterm sgr0)

# Build
build:
	@echo "$(GREEN)Building project...$(RESET)"
	@$(MAKE) -s check-dependencies
	@$(MAKE) -s install-python-dependencies
	@$(MAKE) -s install-pre-commit-hooks
	@echo "$(GREEN)Build completed successfully.$(RESET)"

check-dependencies:
	@echo "$(YELLOW)Checking dependencies...$(RESET)"
	@$(MAKE) -s check-system
	@$(MAKE) -s check-python
	@$(MAKE) -s check-poetry
	@$(MAKE) -s check-tmux
	@echo "$(GREEN)Dependencies checked successfully.$(RESET)"

check-system:
	@echo "$(YELLOW)Checking system...$(RESET)"
	@if [ "$(shell uname)" = "Darwin" ]; then \
		echo "$(BLUE)macOS detected.$(RESET)"; \
	elif [ "$(shell uname)" = "Linux" ]; then \
		if [ -f "/etc/manjaro-release" ]; then \
			echo "$(BLUE)Manjaro Linux detected.$(RESET)"; \
		else \
			echo "$(BLUE)Linux detected.$(RESET)"; \
		fi; \
	elif [ "$$(uname -r | grep -i microsoft)" ]; then \
		echo "$(BLUE)Windows Subsystem for Linux detected.$(RESET)"; \
	else \
		echo "$(RED)Unsupported system detected. Please use macOS, Linux, or Windows Subsystem for Linux (WSL).$(RESET)"; \
		exit 1; \
	fi

check-python:
	@echo "$(YELLOW)Checking Python installation...$(RESET)"
	@if command -v python$(PYTHON_VERSION) > /dev/null; then \
		echo "$(BLUE)$(shell python$(PYTHON_VERSION) --version) is already installed.$(RESET)"; \
	else \
		echo "$(RED)Python $(PYTHON_VERSION) is not installed. Please install Python $(PYTHON_VERSION) to continue.$(RESET)"; \
		exit 1; \
	fi

check-poetry:
	@echo "$(YELLOW)Checking Poetry installation...$(RESET)"
	@if command -v poetry > /dev/null; then \
		POETRY_VERSION=$(shell poetry --version 2>&1 | sed -E 's/Poetry \(version ([0-9]+\.[0-9]+\.[0-9]+)\)/\1/'); \
		IFS='.' read -r -a POETRY_VERSION_ARRAY <<< "$$POETRY_VERSION"; \
		if [ $${POETRY_VERSION_ARRAY[0]} -gt 1 ] || ([ $${POETRY_VERSION_ARRAY[0]} -eq 1 ] && [ $${POETRY_VERSION_ARRAY[1]} -ge 8 ]); then \
			echo "$(BLUE)$(shell poetry --version) is already installed.$(RESET)"; \
		else \
			echo "$(RED)Poetry 1.8 or later is required. You can install poetry by running the following command, then adding Poetry to your PATH:"; \
			echo "$(RED) curl -sSL https://install.python-poetry.org | python$(PYTHON_VERSION) -$(RESET)"; \
			echo "$(RED)More detail here: https://python-poetry.org/docs/#installing-with-the-official-installer$(RESET)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)Poetry is not installed. You can install poetry by running the following command, then adding Poetry to your PATH:"; \
		echo "$(RED) curl -sSL https://install.python-poetry.org | python$(PYTHON_VERSION) -$(RESET)"; \
		echo "$(RED)More detail here: https://python-poetry.org/docs/#installing-with-the-official-installer$(RESET)"; \
		exit 1; \
	fi

check-tmux:
	@echo "$(YELLOW)Checking tmux installation...$(RESET)"
	@if command -v tmux > /dev/null; then \
		echo "$(BLUE)$(shell tmux -V) is already installed.$(RESET)"; \
	else \
		echo "$(YELLOW)╔════════════════════════════════════════════════════════════════════════════╗$(RESET)"; \
		echo "$(YELLOW)║ OPTIONAL: tmux is not installed.                                          ║$(RESET)"; \
		echo "$(YELLOW)║ Some advanced terminal features may not work without tmux.                ║$(RESET)"; \
		echo "$(YELLOW)║ You can install it if needed, but it's not required for development.      ║$(RESET)"; \
		echo "$(YELLOW)╚════════════════════════════════════════════════════════════════════════════╝$(RESET)"; \
	fi

install-python-dependencies:
	@echo "$(GREEN)Installing Python dependencies...$(RESET)"
	@if [ -z "${TZ}" ]; then \
		echo "Defaulting TZ (timezone) to UTC"; \
		export TZ="UTC"; \
	fi
	poetry env use python$(PYTHON_VERSION)
	@if [ "$(shell uname)" = "Darwin" ]; then \
		echo "$(BLUE)Installing chroma-hnswlib...$(RESET)"; \
		export HNSWLIB_NO_NATIVE=1; \
		poetry run pip install chroma-hnswlib; \
	fi
	@if [ -n "${POETRY_GROUP}" ]; then \
		echo "Installing only POETRY_GROUP=${POETRY_GROUP}"; \
		poetry install --only $${POETRY_GROUP}; \
	else \
		poetry install --with dev,test,runtime; \
	fi
	@if [ "${INSTALL_PLAYWRIGHT}" != "false" ] && [ "${INSTALL_PLAYWRIGHT}" != "0" ]; then \
		if [ -f "/etc/manjaro-release" ]; then \
			echo "$(BLUE)Detected Manjaro Linux. Installing Playwright dependencies...$(RESET)"; \
			poetry run pip install playwright; \
			poetry run playwright install chromium; \
		else \
			if [ ! -f cache/playwright_chromium_is_installed.txt ]; then \
				echo "Running playwright install --with-deps chromium..."; \
				poetry run playwright install --with-deps chromium; \
				mkdir -p cache; \
				touch cache/playwright_chromium_is_installed.txt; \
			else \
				echo "Setup already done. Skipping playwright installation."; \
			fi \
		fi \
	else \
		echo "Skipping Playwright installation (INSTALL_PLAYWRIGHT=${INSTALL_PLAYWRIGHT})."; \
	fi
	@echo "$(GREEN)Python dependencies installed successfully.$(RESET)"

install-pre-commit-hooks: check-python check-poetry install-python-dependencies
	@echo "$(YELLOW)Installing pre-commit hooks...$(RESET)"
	@git config --unset-all core.hooksPath || true
	@poetry run pre-commit install --config $(PRE_COMMIT_CONFIG_PATH)
	@echo "$(GREEN)Pre-commit hooks installed successfully.$(RESET)"

lint: install-pre-commit-hooks
	@echo "$(YELLOW)Running linters...$(RESET)"
	@poetry run pre-commit run --all-files --show-diff-on-failure --config $(PRE_COMMIT_CONFIG_PATH)

# Proto compilation
.PHONY: compile-protos
compile-protos:
	@echo "$(GREEN)Compiling Protocol Buffer definitions...$(RESET)"
	@python backend/scripts/build/compile_protos.py
	@echo "$(GREEN)Proto compilation completed.$(RESET)"

.PHONY: update-openapi
update-openapi:
	@echo "$(GREEN)Regenerating OpenAPI schema...$(RESET)"
	@python backend/scripts/build/update_openapi.py
	@echo "$(GREEN)OpenAPI schema updated at openapi.json.$(RESET)"

# Start backend
start-backend:
	@echo "$(YELLOW)Starting backend...$(RESET)"
	@poetry run uvicorn backend.server.listen:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload --reload-exclude "./workspace"

# Run the app
run:
	@echo "$(YELLOW)Running the app...$(RESET)"
	@mkdir -p logs
	@echo "$(YELLOW)Starting backend server...$(RESET)"
	@poetry run uvicorn backend.server.listen:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) &
	@echo "$(YELLOW)Waiting for the backend to start...$(RESET)"
	@until nc -z localhost $(BACKEND_PORT); do sleep 0.1; done
	@echo "$(GREEN)Backend started successfully on $(BACKEND_HOST_PORT).$(RESET)"
	@echo "$(GREEN)Launch TUI with: python -m backend.tui$(RESET)"

# Setup config.toml
setup-config:
	@echo "$(YELLOW)Setting up Forge configuration...$(RESET)"
	@$(MAKE) setup-config-prompts
	@mv $(CONFIG_FILE).tmp $(CONFIG_FILE)
	@echo "$(GREEN)Config.toml setup completed.$(RESET)"

setup-config-prompts:
	@echo "# Forge Configuration File" > $(CONFIG_FILE).tmp
	@echo "[core]" >> $(CONFIG_FILE).tmp

	@read -p "Enter your workspace directory (as absolute path) [default: $(DEFAULT_WORKSPACE_DIR)]: " workspace_dir; \
	 workspace_dir=$${workspace_dir:-$(DEFAULT_WORKSPACE_DIR)}; \
	 echo "workspace_base=\"$$workspace_dir\"" >> $(CONFIG_FILE).tmp

	@echo "" >> $(CONFIG_FILE).tmp

	@echo "[llm]" >> $(CONFIG_FILE).tmp
	@read -p "Enter your LLM model name [default: $(DEFAULT_MODEL)]: " llm_model; \
	 llm_model=$${llm_model:-$(DEFAULT_MODEL)}; \
	 echo "model=\"$$llm_model\"" >> $(CONFIG_FILE).tmp

	@read -p "Enter your LLM API key: " llm_api_key; \
	 echo "api_key=\"$$llm_api_key\"" >> $(CONFIG_FILE).tmp

	@read -p "Enter your LLM base URL [mostly used for local LLMs, leave blank if not needed - example: http://localhost:5001/v1/]: " llm_base_url; \
	 if [[ ! -z "$$llm_base_url" ]]; then echo "base_url=\"$$llm_base_url\"" >> $(CONFIG_FILE).tmp; fi

setup-config-basic:
	@printf '%s\n' \
	'# Forge Configuration' \
	'[core]' \
	'workspace_base="./workspace"' \
	> config.toml
	@echo "$(GREEN)config.toml created.$(RESET)"

# Clean up all caches
clean:
	@echo "$(YELLOW)Cleaning up caches...$(RESET)"
	@rm -rf backend/.cache
	@echo "$(GREEN)Caches cleaned up successfully.$(RESET)"

# Help
help:
	@echo "$(BLUE)Usage: make [target]$(RESET)"
	@echo "Targets:"
	@echo "  $(GREEN)build$(RESET)               - Build project, including environment setup and dependencies."
	@echo "  $(GREEN)lint$(RESET)                - Run linters on the project."
	@echo "  $(GREEN)setup-config$(RESET)        - Setup the configuration for Forge by providing LLM API key,"
	@echo "                        LLM Model name, and workspace directory."
	@echo "  $(GREEN)start-backend$(RESET)       - Start the backend server for the Forge project."
	@echo "  $(GREEN)run$(RESET)                 - Start the backend, then launch the TUI with: python -m backend.tui"
	@echo "  $(GREEN)help$(RESET)                - Display this help message, providing information on available targets."

# Phony targets
.PHONY: build check-dependencies check-system check-python check-poetry install-python-dependencies install-pre-commit-hooks lint start-backend run setup-config setup-config-prompts setup-config-basic clean help
