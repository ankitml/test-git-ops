# Quick Start Guide

## Initial Setup (One Time)

```bash
cd /Users/ankit/Documents/repos/test_enterprise_branch

# 1. Create virtual environment and install dependencies
make setup

# 2. Create test repositories (in /tmp)
make setup-repos

# 3. Copy scripts from main enterprise repo
make copy-scripts
```

This creates:
- `.venv/` - Python virtual environment
- `/tmp/test-community-sync/community-repo` - Fake community repo
- `/tmp/test-community-sync/community-origin` - Acts as remote origin for community
- `/tmp/test-community-sync/enterprise-repo` - Fake enterprise repo
- `/tmp/test-community-sync/enterprise-origin` - Acts as remote origin for enterprise
- `scripts/` - Copied sync scripts with `--skip-validation` support

## Testing Workflow

### Option 1: Interactive Test Runner (Recommended)

```bash
make run-test
```

This gives you a menu:
1. Show current git state
2-4. Add commits to community repo (1, 3, or 5 commits)
5-7. Sync commits (1, 3, or 5 commits) with `--skip-validation`
8. Create conflicting commit (for testing conflict resolution)
9. Exit

### Option 2: Manual Commands

```bash
# Add some commits to community repo
make add-commits N=5

# Go to enterprise repo and run sync
cd /tmp/test-community-sync/enterprise-repo
git fetch community

# Run the sync script with --skip-validation
/Users/ankit/Documents/repos/test_enterprise_branch/scripts/rebase-community-batch.sh \
  --skip-validation \
  --max-commits 3

# Check results
git log --oneline --graph -10
```

## What Gets Tested

✅ Git rebase logic
✅ Batch commit processing
✅ Conflict detection (CI validation is skipped)
✅ Enterprise patches stay on top
✅ History tag creation
✅ Force-push with lease

## Cleanup

```bash
# Remove everything (virtual env + test repos + copied scripts)
make clean

# Then you can start fresh with:
make setup
make setup-repos
make copy-scripts
```

## Tips

- Test repos are in `/tmp/test-community-sync/` - they're ephemeral
- The `--skip-validation` flag skips CI validation for fast testing
- You can inspect repos manually: `cd /tmp/test-community-sync/enterprise-repo && git log`
- Run `make help` anytime to see available commands
