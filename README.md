# Community Sync Testing Framework

Testing framework for enterprise community sync scripts. Tests git rebase/squash operations between community and enterprise repositories.

## Configuration

**Variables (in Makefile):**
```bash
ENTERPRISE_REPO := /path/to/your/enterprise-repo    # Your local enterprise repo
COMMUNITY_REPO_URL := https://github.com/your-org/community-repo.git  # Upstream community
```

**Repository Workflow:**
1. **Community**: `https://github.com/your-org/community-repo.git` (upstream open source)
2. **Enterprise**: `/path/to/your/enterprise-repo` (your local fork + patches)
3. **Test repos**: Created in `/tmp/test-community-sync/` (ephemeral)

## How It Works

1. **Setup**: Create fake community/enterprise repos in `/tmp/` with known commit states
2. **Symlink**: Link scripts from your enterprise repo into test repos
3. **Test**: Run rebase/squash operations to verify git logic works correctly
4. **Cleanup**: Remove all test repos (safe since they're temporary)

## Available Commands

```bash
# Setup (run once)
make setup              # Create Python virtual environment
make setup-repos        # Create test repositories in /tmp/
make copy-scripts       # Symlink scripts from $(ENTERPRISE_REPO)

# Interactive Testing
make run-test           # Interactive rebase testing (menu-driven)
make run-squash-test    # Interactive squash testing (menu-driven)

# Automated Testing
make test               # Run all automated tests (rebase + squash)
make test-rebase        # Run automated rebase tests only
make test-squash        # Run automated squash tests only

# Utility
make add-commits N=5    # Add N commits to community repo
make clean              # Remove venv and test repos
make help               # Show all commands
```

## Testing Methodologies

### Interactive Testing (Manual Exploration)

**How it works:** Menu-driven interfaces where you select scenarios step-by-step. Perfect for learning, debugging, and exploring edge cases.

**Rebase Testing (`make run-test`):**
- Interactive menu with 9+ options
- Add commits to community repo (1, 3, or 5 at a time)
- Sync commits with `--skip-validation`
- Create conflict scenarios for testing
- Verify enterprise patch preservation

**Squash Testing (`make run-squash-test`):**
- Interactive menu with 11+ options
- Create multiple enterprise patches
- Test dry-run, actual, and force squash operations
- Inspect created tags and history preservation
- Reset to different test scenarios

### Automated Testing (CI/Ready Validation)

**How it works:** Non-interactive test suites that automatically set up scenarios, execute operations, and validate results. Perfect for regression testing and CI pipelines.

**Automated Rebase Tests (`make test-rebase`):**
- Includes all rebase scenarios (single commit, batch sync, no commits, multiple cycles)
- Automatically validates patch preservation and git state correctness

**Automated Squash Tests (`make test-squash`):**
- Includes all squash scenarios (dry-run, actual operations, edge cases)
- Validates tag creation, history preservation, and git state changes

**Validation Framework:**
- Captures git state before/after operations
- Compares commit counts, HEAD positions, and tags
- Reports detailed pass/fail results with expected/actual values
- Automatically cleans up test repositories

## Directory Structure

```
.
├── Makefile                    # Commands and configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── src/
│   ├── setup_repos.py         # Create /tmp test repos
│   ├── run_manual_test.py     # Interactive rebase testing
│   ├── run_squash_test.py     # Interactive squash testing
│   ├── test_rebase_automated.py  # Automated rebase test suite
│   ├── test_squash_automated.py  # Automated squash test suite
│   └── test_helpers.py        # Validation framework
├── scripts/                   # Symlinked from $(ENTERPRISE_REPO)
└── /tmp/test-community-sync/  # Test repositories (created by setup)
```

## Testing Philosophy

- **Ephemeral**: All test repos are temporary and disposable
- **Isolated**: No impact on your actual repositories
- **Interactive**: Step-by-step testing with clear menus
- **Language-agnostic**: Works with any script type (.sh, .rs, .py)
- **Fast**: Uses `--skip-validation` to skip CI for quick iteration

## Example Workflow

```bash
# Initial setup
make setup
make setup-repos
make copy-scripts

# Test rebase operations
make run-test
# → Select "3" to add 3 commits to community
# → Select "6" to sync 3 commits with --skip-validation

# Test squash operations
make run-squash-test
# → Select "1" to setup fresh repos
# → Select "8" to test actual squash operation

# Cleanup when done
make clean
```

# Python downtime detecter
```
export PGPASSWORD='<>'
  python3 scripts/postgres_downtime_probe.py \
    --host localhost \
    --port 9990 \
    --user paradedb \
    --dbname paradedb \
    --table-name public.upgrade_probe \
    --interval 0.1 \
    --log-file ~/postgres_downtime_probe.csv
```
