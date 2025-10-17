#!/usr/bin/env python3
"""
Simplified Community Sync Test

Tests the core rebase scenario:
1. Community has 3 commits
2. Enterprise has those 3 commits + 1 enterprise commit on top
3. New commit added to community
4. Rebase puts enterprise commit on top of the new community commit

This test includes CI validation to ensure the rebase workflow works end-to-end.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
TEST_DIR = Path(tempfile.mkdtemp(prefix="test-community-sync-"))
COMMUNITY_REPO = TEST_DIR / "community-repo"
ENTERPRISE_REPO = TEST_DIR / "enterprise-repo"

def run(cmd, cwd=None, check=True, capture_output=True):
    """Run a command and return result."""
    print(f"🔧 Running: {cmd}")
    if cwd:
        print(f"   in: {cwd}")

    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=capture_output,
        text=True
    )

    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return result

def setup_git_repo(name, email):
    """Configure git user in a repository."""
    run(f"git config user.name '{name}'", cwd=None, check=False)
    run(f"git config user.email '{email}'", cwd=None, check=False)

def create_commit(repo_path, message, filename=None):
    """Create a commit in the given repository."""
    if filename is None:
        filename = f"file_{datetime.now().strftime('%H%M%S')}.txt"

    file_path = repo_path / filename
    content = f"{message}\nCreated at {datetime.now()}\n"

    file_path.write_text(content)
    run(f"git add {filename}", cwd=repo_path)
    run(f"git commit -m '{message}'", cwd=repo_path)

    return file_path

def get_commit_count(repo_path):
    """Get total commit count in repository."""
    result = run("git rev-list --count HEAD", cwd=repo_path)
    return int(result.stdout.strip())

def get_commit_messages(repo_path, max_count=10):
    """Get recent commit messages."""
    result = run(f"git log --oneline -{max_count}", cwd=repo_path)
    return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

def show_repo_state(name, repo_path):
    """Show current state of repository."""
    print(f"\n📋 {name} Repository State:")
    print(f"   Path: {repo_path}")
    print(f"   Commits: {get_commit_count(repo_path)}")
    print("   Recent commits:")
    for msg in get_commit_messages(repo_path, 5):
        print(f"     {msg}")

def setup_test_scenario():
    """Set up the initial git universe."""
    print(f"\n🌍 Setting up test universe in {TEST_DIR}")

    # Create directories
    COMMUNITY_REPO.mkdir(parents=True, exist_ok=True)
    ENTERPRISE_REPO.mkdir(parents=True, exist_ok=True)

    # Setup community repo
    print("\n🏗️  Creating community repository...")
    run("git init", cwd=COMMUNITY_REPO)
    setup_git_repo("Community User", "community@example.com")

    # Create 3 community commits
    print("📝 Creating 3 community commits...")
    create_commit(COMMUNITY_REPO, "feat: add core functionality", "core.py")
    create_commit(COMMUNITY_REPO, "fix: resolve import issues", "utils.py")
    create_commit(COMMUNITY_REPO, "docs: update README", "README.md")

    # Setup enterprise repo as a clone of community
    print("\n🏢 Creating enterprise repository...")
    run("git init", cwd=ENTERPRISE_REPO)
    setup_git_repo("Enterprise User", "enterprise@example.com")

    # Copy community content to enterprise
    shutil.copytree(COMMUNITY_REPO / ".git", ENTERPRISE_REPO / ".git", dirs_exist_ok=True)
    for item in COMMUNITY_REPO.iterdir():
        if item.name != ".git":
            if item.is_file():
                shutil.copy2(item, ENTERPRISE_REPO)
            else:
                shutil.copytree(item, ENTERPRISE_REPO / item.name, dirs_exist_ok=True)

    # Create enterprise-specific commit on top
    print("📝 Creating enterprise commit...")
    create_commit(ENTERPRISE_REPO, "feat: add enterprise authentication", "auth.py")

    # Set up proper branch structure for rebase script
    print("🔧 Setting up proper branch structure...")
    # Ensure we're on main branch (git init creates it by default now)
    run("git checkout main", cwd=ENTERPRISE_REPO)

    # Set up local origin pointing to the enterprise repo itself
    run(f"git remote add origin {ENTERPRISE_REPO}", cwd=ENTERPRISE_REPO)
    run("git fetch origin", cwd=ENTERPRISE_REPO)

    # Create origin/main reference pointing to current main
    run("git update-ref refs/remotes/origin/main main", cwd=ENTERPRISE_REPO)

    # Show initial state
    show_repo_state("Community", COMMUNITY_REPO)
    show_repo_state("Enterprise", ENTERPRISE_REPO)

    return True

def test_rebase_scenario():
    """Test the main rebase scenario."""
    print("\n" + "="*60)
    print("🧪 TESTING: Community Rebase Scenario")
    print("="*60)

    # Get initial state
    initial_community_commits = get_commit_count(COMMUNITY_REPO)
    initial_enterprise_commits = get_commit_count(ENTERPRISE_REPO)

    print(f"\n📊 Initial state:")
    print(f"   Community: {initial_community_commits} commits")
    print(f"   Enterprise: {initial_enterprise_commits} commits")

    # Add new commit to community
    print("\n📝 Adding new commit to community...")
    create_commit(COMMUNITY_REPO, "feat: add new community feature", "new_feature.py")

    new_community_commits = get_commit_count(COMMUNITY_REPO)
    print(f"   Community now has: {new_community_commits} commits (+1)")

    # Setup enterprise repo to use community as remote
    print("\n🔗 Setting up community remote in enterprise...")
    run(f"git remote add community {COMMUNITY_REPO}", cwd=ENTERPRISE_REPO)
    run("git fetch community", cwd=ENTERPRISE_REPO)

    # Get the rebase script path (assuming it exists in ../scripts)
    scripts_dir = Path(__file__).parent.parent / "scripts"
    rebase_script = scripts_dir / "rebase-community-batch.sh"

    if not rebase_script.exists():
        print(f"❌ Rebase script not found: {rebase_script}")
        print("   This test requires the rebase scripts to be available")
        return False

    # Run the rebase script (now includes CI validation)
    print("\n🔄 Running rebase script with CI validation...")
    cmd = f"{rebase_script} --max-commits 1"

    try:
        result = run(cmd, cwd=ENTERPRISE_REPO, check=False)
        if result.returncode != 0:
            print(f"❌ Rebase script failed with exit code {result.returncode}")
            print(f"stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to run rebase script: {e}")
        return False

    # Check final state
    final_enterprise_commits = get_commit_count(ENTERPRISE_REPO)
    final_community_commits = get_commit_count(COMMUNITY_REPO)

    print(f"\n📊 Final state:")
    print(f"   Community: {final_community_commits} commits")
    print(f"   Enterprise: {final_enterprise_commits} commits")

    # Show final repository states
    show_repo_state("Community", COMMUNITY_REPO)
    show_repo_state("Enterprise", ENTERPRISE_REPO)

    # Validate results
    print(f"\n✅ Validation:")

    # Enterprise should have one more commit than before (synced the community commit)
    expected_enterprise_commits = initial_enterprise_commits + 1
    if final_enterprise_commits == expected_enterprise_commits:
        print(f"   ✅ Enterprise commit count correct: {final_enterprise_commits}")
    else:
        print(f"   ❌ Enterprise commit count wrong: expected {expected_enterprise_commits}, got {final_enterprise_commits}")
        return False

    # Check if enterprise commit is still on top
    enterprise_messages = get_commit_messages(ENTERPRISE_REPO, 3)
    if "feat: add enterprise authentication" in enterprise_messages[0]:
        print(f"   ✅ Enterprise commit preserved on top: {enterprise_messages[0]}")
    else:
        print(f"   ❌ Enterprise commit not on top. Recent commits: {enterprise_messages}")
        return False

    # Check if community feature was synced
    if any("new community feature" in msg for msg in enterprise_messages):
        print(f"   ✅ Community commit synced successfully")
    else:
        print(f"   ❌ Community commit not found in enterprise. Recent commits: {enterprise_messages}")
        return False

    return True

def cleanup():
    """Clean up test repositories."""
    print(f"\n🧹 Cleaning up test directory: {TEST_DIR}")
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    print("✅ Cleanup complete")

def main():
    """Run the simplified community sync test."""
    print("🚀 Simplified Community Sync Test")
    print("="*50)
    print("This test verifies that enterprise commits stay on top")
    print("when syncing new community commits via rebase.")

    try:
        # Setup the git universe
        if not setup_test_scenario():
            print("❌ Failed to setup test scenario")
            return 1

        # Run the rebase test
        if test_rebase_scenario():
            print("\n🎉 TEST PASSED!")
            print("Enterprise commit successfully rebased on top of new community commit")
            return 0
        else:
            print("\n💥 TEST FAILED!")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        cleanup()

if __name__ == "__main__":
    sys.exit(main())