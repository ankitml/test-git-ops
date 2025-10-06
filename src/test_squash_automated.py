#!/usr/bin/env python3
"""
Automated squash testing runner.

Tests enterprise patch squash operations without user interaction.
Includes setup, execution, and validation phases.
"""

import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_helpers import (
    run, get_git_state, validate_squash_result,
    print_test_results, TestResult,
    COMMUNITY_REPO, ENTERPRISE_REPO, TEST_DIR
)

# Import squash test functions
from run_squash_test import setup_squash_test_repos


def add_enterprise_patches(count: int) -> bool:
    """Add enterprise patches for testing."""
    print(f"\n📝 Adding {count} enterprise patches...")

    try:
        from run_squash_test import add_enterprise_patches
        add_enterprise_patches(count)
        print(f"✅ Added {count} enterprise patches")
        return True
    except Exception as e:
        print(f"❌ Failed to add enterprise patches: {e}")
        return False


def test_squash_dry_run(commit_count: int) -> List[TestResult]:
    """Test squash operation with dry-run flag."""
    print("\n" + "="*50)
    print(f"🧪 TESTING: Squash Dry Run ({commit_count} patches)")
    print("="*50)

    results = []

    # Setup
    setup_squash_test_repos()

    # Add enterprise patches
    if not add_enterprise_patches(commit_count):
        results.append(TestResult("Squash Dry Run Setup", False, f"Failed to add {commit_count} patches"))
        return results

    # Get state before dry run
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Run dry-run
    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        results.append(TestResult("Squash Dry Run", False, "Squash script not found"))
        return results

    cmd = f"{squash_script} --dry-run -m 'test: squashed enterprise patches'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    dry_run_success = result.returncode == 0

    # Get state after dry run (should be unchanged)
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    # Validate: state should be unchanged after dry run
    unchanged = (enterprise_before.head_sha == enterprise_after.head_sha and
                enterprise_before.ahead_count == enterprise_after.ahead_count)

    results.append(TestResult(
        "Squash Dry Run Validation",
        dry_run_success and unchanged,
        f"Dry run succeeded: {dry_run_success}, State unchanged: {unchanged}",
        expected={"dry_run_success": True, "unchanged": True},
        actual={"dry_run_success": dry_run_success, "unchanged": unchanged}
    ))

    return results


def test_squash_actual(commit_count: int) -> List[TestResult]:
    """Test actual squash operation."""
    print("\n" + "="*50)
    print(f"🧪 TESTING: Actual Squash ({commit_count} patches)")
    print("="*50)

    results = []

    # Setup
    setup_squash_test_repos()

    # Add enterprise patches
    if not add_enterprise_patches(commit_count):
        results.append(TestResult("Squash Actual Setup", False, f"Failed to add {commit_count} patches"))
        return results

    # Get state before squash
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Run actual squash with force flag to avoid interactive prompts
    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        results.append(TestResult("Squash Actual", False, "Squash script not found"))
        return results

    cmd = f"{squash_script} --force -m 'test: squashed enterprise patches'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    squash_success = result.returncode == 0

    if not squash_success:
        results.append(TestResult("Squash Actual", False, f"Squash script failed with exit code {result.returncode}"))
        if result.stderr:
            print(f"Squash error: {result.stderr}")
        return results

    # Get state after squash
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    # Validate squash result
    validation = validate_squash_result(enterprise_before, enterprise_after, commit_count)
    results.append(validation)

    return results


def test_squash_no_patches() -> List[TestResult]:
    """Test squash when there are no patches to squash."""
    print("\n" + "="*50)
    print("🧪 TESTING: Squash No Patches")
    print("="*50)

    results = []

    # Setup without adding patches
    setup_squash_test_repos()

    # Get state before
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Try to squash (should handle gracefully)
    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        results.append(TestResult("Squash No Patches", False, "Squash script not found"))
        return results

    cmd = f"{squash_script} --force -m 'test: should do nothing'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    # Script should exit successfully when no patches to squash
    no_patches_handled = result.returncode == 0

    # Get state after (should be unchanged)
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    unchanged = (enterprise_before.head_sha == enterprise_after.head_sha)

    results.append(TestResult(
        "Squash No Patches Validation",
        no_patches_handled and unchanged,
        f"No patches handled: {no_patches_handled}, State unchanged: {unchanged}",
        expected={"no_patches_handled": True, "unchanged": True},
        actual={"no_patches_handled": no_patches_handled, "unchanged": unchanged}
    ))

    return results


def test_squash_single_patch() -> List[TestResult]:
    """Test squash with single patch (edge case)."""
    print("\n" + "="*50)
    print("🧪 TESTING: Squash Single Patch")
    print("="*50)

    results = []

    # Setup
    setup_squash_test_repos()

    # Add only 1 patch
    if not add_enterprise_patches(1):
        results.append(TestResult("Squash Single Setup", False, "Failed to add 1 patch"))
        return results

    # Get state before
    enterprise_before = get_git_state(ENTERPRISE_REPO)

    # Run squash
    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        results.append(TestResult("Squash Single", False, "Squash script not found"))
        return results

    cmd = f"{squash_script} --force -m 'test: single patch'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    single_patch_handled = result.returncode == 0

    # Get state after
    enterprise_after = get_git_state(ENTERPRISE_REPO)

    # Single patch shouldn't be squashed (nothing to squash with)
    unchanged = (enterprise_before.head_sha == enterprise_after.head_sha)

    results.append(TestResult(
        "Squash Single Patch Validation",
        single_patch_handled and unchanged,
        f"Single patch handled: {single_patch_handled}, State unchanged: {unchanged}",
        expected={"single_patch_handled": True, "unchanged": True},
        actual={"single_patch_handled": single_patch_handled, "unchanged": unchanged}
    ))

    return results


def cleanup_test_repos():
    """Clean up test repositories."""
    print("\n🧹 Cleaning up test repositories...")
    if TEST_DIR.exists():
        run(f"rm -rf {TEST_DIR}")
    print("✅ Cleanup complete")


def main():
    """Run all automated squash tests."""
    print("🚀 Automated Squash Test Suite")
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
        all_results.extend(test_squash_no_patches())
        all_results.extend(test_squash_single_patch())
        all_results.extend(test_squash_dry_run(3))
        all_results.extend(test_squash_dry_run(5))
        all_results.extend(test_squash_actual(3))
        all_results.extend(test_squash_actual(5))

        # Print results
        success = print_test_results(all_results)

        if success:
            print("\n🎉 All squash tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some squash tests failed!")
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