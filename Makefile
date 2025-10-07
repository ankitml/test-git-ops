.PHONY: setup clean test help setup-repos copy-scripts add-commits run-test run-squash-test

# Load configuration from .env file
include .env

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

help:
	@echo "Available targets:"
	@echo "  make setup              - Create virtual environment and install dependencies"
	@echo "  make setup-repos        - Create test repositories in /tmp/test-community-sync"
	@echo "  make copy-scripts       - Symlink scripts from $(ENTERPRISE_REPO)"
	@echo "  make add-commits N=3    - Add N commits to community repo (default: 3)"
	@echo ""
	@echo "Interactive Testing:"
	@echo "  make run-test           - Run interactive manual test runner (rebase testing)"
	@echo "  make run-squash-test    - Run interactive squash test runner"
	@echo ""
	@echo "Automated Testing:"
	@echo "  make test               - Run all automated tests (rebase + squash)"
	@echo "  make test-rebase        - Run automated rebase tests only"
	@echo "  make test-squash        - Run automated squash tests only"
	@echo ""
	@echo "Utility:"
	@echo "  make clean              - Remove virtual environment and test repos"
	@echo "  make help               - Show this help message"

setup: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: requirements.txt
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV_DIR)
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Setup complete! Activate with: source $(VENV_DIR)/bin/activate"

setup-repos: setup
	@echo "Setting up test repositories..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/setup_repos.py
	@echo "✅ Test repos created in /tmp/test-community-sync"

copy-scripts: setup
	@echo "Creating symlinks to scripts from $(ENTERPRISE_REPO)..."
	@if [ -L scripts ]; then \
		echo "Removing existing symlink..."; \
		rm scripts; \
	elif [ -d scripts ]; then \
		echo "Removing existing scripts directory..."; \
		rm -rf scripts; \
	fi
	ln -s $(ENTERPRISE_REPO)/scripts scripts
	@echo "✅ Scripts symlinked to ./scripts/"
	@if [ -d /tmp/test-community-sync/enterprise-repo ]; then \
		echo "Creating scripts symlink in enterprise test repo..."; \
		if [ -L /tmp/test-community-sync/enterprise-repo/scripts ]; then \
			rm /tmp/test-community-sync/enterprise-repo/scripts; \
		elif [ -d /tmp/test-community-sync/enterprise-repo/scripts ]; then \
			rm -rf /tmp/test-community-sync/enterprise-repo/scripts; \
		fi; \
		ln -s $(ENTERPRISE_REPO)/scripts /tmp/test-community-sync/enterprise-repo/scripts; \
		echo "✅ Scripts symlinked to enterprise test repo"; \
	else \
		echo "⚠️  Enterprise test repo not found - run 'make setup-repos' first"; \
	fi

add-commits: setup
	@echo "Adding $(or $(N),3) commits to community repo..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/setup_repos.py add-commits $(or $(N),3)

run-test: setup
	@echo "Starting interactive test runner..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/run_manual_test.py

run-squash-test: setup
	@echo "Starting interactive squash test runner..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/run_squash_test.py

test: setup copy-scripts
	@echo "Running automated tests..."
	@echo "Running rebase tests..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/test_rebase_automated.py
	@echo "Running squash tests..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/test_squash_automated.py

test-rebase: setup copy-scripts
	@echo "Running automated rebase tests..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/test_rebase_automated.py

test-squash: setup copy-scripts
	@echo "Running automated squash tests..."
	ENTERPRISE_REPO=$(ENTERPRISE_REPO) $(PYTHON) src/test_squash_automated.py

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_DIR)
	rm -rf /tmp/test-community-sync
	@if [ -L scripts ]; then \
		echo "Removing scripts symlink..."; \
		rm scripts; \
	fi
	@echo "✅ Cleanup complete!"
