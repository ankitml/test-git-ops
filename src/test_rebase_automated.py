#!/usr/bin/env python3
"""
Automated rebase testing runner.

Tests community sync rebase operations without user interaction.
Includes setup, execution, and validation phases.
"""

import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_helpers import (
    run, get_git_state, count_commits_between, validate_rebase_result,
    print_test_results, setup_test_scenario, TestResult,
    COMMUNITY_REPO, ENTERPRISE_REPO, TEST_DIR
)


def add_community_commits(count: int) -> bool:
    """Add commits to community repo."""
    print(f"\n📝 Adding {count} commits to community repo...")

    try:
        from setup_repos import add_community_commits
        add_community_commits(count)
        print(f"✅ Added {count} commits to community repo")
        return True
    except Exception as e:
        print(f"❌ Failed to add community commits: {e}")
        return False


def sync_commits(max_commits: int = 3) -> bool:
    """Sync commits from community to enterprise using rebase script."""
    print(f"\n🔄 Syncing {max_commits} commits from community to enterprise...")

    scripts_dir = ENTERPRISE_REPO / "scripts"
    rebase_script = scripts_dir / "rebase-community-batch.sh"

    if not rebase_script.exists():
        print(f"❌ Rebase script not found: {rebase_script}")
        return False

    cmd = f"{rebase_script} --skip-validation --max-commits {max_commits}"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    if result.returncode == 0:
        print(f"✅ Successfully synced {max_commits} commits")
        return True
    else:
        print(f"❌ Sync failed with exit code {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return False


def test_single_commit_sync() -> List[TestResult]:
    """Test syncing a single commit."""
    print("\n" + "="*50)
    print("🧪 TESTING: Single Commit Sync")
    print("="*50)

    results = []

    # Setup
    community_state, enterprise_state = setup_test_scenario()

    # Add 1 community commit
    if not add_community_commits(1):
        results.append(TestResult("Single Commit Setup", False, "Failed to add community commits"))
        return results

    # Get enterprise state before sync
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Sync the commit
    if not sync_commits(1):
        results.append(TestResult("Single Commit Sync", False, "Rebase script failed"))
        return results

    # Get final state and validate
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    validation = validate_rebase_result(enterprise_before, enterprise_after, 1)
    results.append(validation)

    return results


def test_batch_commit_sync() -> List[TestResult]:
    """Test syncing multiple commits."""
    print("\n" + "="*50)
    print("🧪 TESTING: Batch Commit Sync (3 commits)")
    print("="*50)

    results = []

    # Setup
    community_state, enterprise_state = setup_test_scenario()

    # Add 3 community commits
    if not add_community_commits(3):
        results.append(TestResult("Batch Commit Setup", False, "Failed to add community commits"))
        return results

    # Get enterprise state before sync
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Sync the commits
    if not sync_commits(3):
        results.append(TestResult("Batch Commit Sync", False, "Rebase script failed"))
        return results

    # Get final state and validate
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    validation = validate_rebase_result(enterprise_before, enterprise_after, 3)
    results.append(validation)

    return results


def test_no_commits_to_sync() -> List[TestResult]:
    """Test when there are no new commits to sync."""
    print("\n" + "="*50)
    print("🧪 TESTING: No Commits to Sync")
    print("="*50)

    results = []

    # Setup
    community_state, enterprise_state = setup_test_scenario()

    # Get enterprise state before sync
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Try to sync (should find no commits)
    if not sync_commits(5):
        results.append(TestResult("No Commits Sync", False, "Rebase script failed when it should handle no commits"))
        return results

    # Get final state and validate
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    # Should have same state (no changes)
    unchanged = (enterprise_before.head_sha == enterprise_after.head_sha and
                enterprise_before.ahead_count == enterprise_after.ahead_count)

    results.append(TestResult(
        "No Commits Validation",
        unchanged,
        "Repository state unchanged when no commits to sync",
        expected={"unchanged": True},
        actual={"unchanged": unchanged, "head_same": enterprise_before.head_sha == enterprise_after.head_sha}
    ))

    return results


def test_multiple_sync_cycles() -> List[TestResult]:
    """Test multiple sync cycles."""
    print("\n" + "="*50)
    print("🧪 TESTING: Multiple Sync Cycles")
    print("="*50)

    results = []

    # Setup
    community_state, enterprise_state = setup_test_scenario()

    # First sync cycle: Add 2 commits
    if not add_community_commits(2):
        results.append(TestResult("Multiple Sync Setup", False, "Failed to add first batch of commits"))
        return results

    enterprise_before_first = get_git_state(ENTERPRISE_REPO)
    if not sync_commits(2):
        results.append(TestResult("First Sync Cycle", False, "First sync failed"))
        return results

    enterprise_after_first = get_git_state(ENTERPRISE_REPO)
    first_validation = validate_rebase_result(enterprise_before_first, enterprise_after_first, 2)
    results.append(first_validation)

    # Second sync cycle: Add 1 more commit
    if not add_community_commits(1):
        results.append(TestResult("Multiple Sync Setup", False, "Failed to add second batch of commits"))
        return results

    enterprise_before_second = get_git_state(ENTERPRISE_REPO)
    if not sync_commits(1):
        results.append(TestResult("Second Sync Cycle", False, "Second sync failed"))
        return results

    enterprise_after_second = get_git_state(ENTERPRISE_REPO)
    second_validation = validate_rebase_result(enterprise_before_second, enterprise_after_second, 1)
    results.append(second_validation)

    return results


def cleanup_test_repos():
    """Clean up test repositories."""
    print("\n🧹 Cleaning up test repositories...")
    if TEST_DIR.exists():
        run(f"rm -rf {TEST_DIR}")
    print("✅ Cleanup complete")


def main():
    """Run all automated rebase tests."""
    print("🚀 Automated Rebase Test Suite")
    print("="*60)

    # Check if scripts directory exists
    scripts_dir = Path(__file__).parent.parent / "scripts"
    if not scripts_dir.exists():
        print("❌ Scripts directory not found!")
        print("Run 'make copy-scripts' first")
        sys.exit(1)

    all_results = []

    try:
        # Run test scenarios
        all_results.extend(test_single_commit_sync())
        all_results.extend(test_batch_commit_sync())
        all_results.extend(test_no_commits_to_sync())
        all_results.extend(test_multiple_sync_cycles())

        # Print results
        success = print_test_results(all_results)

        if success:
            print("\n🎉 All rebase tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some rebase tests failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)
    finally:
        # Always cleanup
        cleanup_test_repos()


if __name__ == "__main__":
    main()