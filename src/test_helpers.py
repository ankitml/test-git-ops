#!/usr/bin/env python3
"""
Test helpers for automated validation of git operations.

Provides functions to verify expected vs actual git states,
create test scenarios, and report results.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

TEST_DIR = Path("/tmp/test-community-sync")
COMMUNITY_REPO = TEST_DIR / "community-repo"
ENTERPRISE_REPO = TEST_DIR / "enterprise-repo"


@dataclass
class GitState:
    """Represents the state of a git repository."""
    commits: List[str]  # List of commit SHAs
    head_sha: str
    branch: str
    tags: List[str]
    is_clean: bool
    ahead_count: int = 0
    behind_count: int = 0


@dataclass
class TestResult:
    """Represents a test result."""
    test_name: str
    passed: bool
    message: str
    expected: Optional[Dict] = None
    actual: Optional[Dict] = None


def run(cmd, cwd=None, check=True, capture_output=True):
    """Run shell command and return result."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
    )
    return result


def get_git_state(repo_path: Path, ref: str = "HEAD") -> GitState:
    """Get current git state of a repository."""
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository not found: {repo_path}")

    # Get commit list
    result = run("git rev-list --reverse HEAD", cwd=repo_path)
    commits = result.stdout.strip().split('\n') if result.stdout.strip() else []

    # Get HEAD SHA
    head_result = run("git rev-parse HEAD", cwd=repo_path)
    head_sha = head_result.stdout.strip()

    # Get current branch
    branch_result = run("git branch --show-current", cwd=repo_path)
    branch = branch_result.stdout.strip()

    # Get tags
    tags_result = run("git tag -l", cwd=repo_path)
    tags = tags_result.stdout.strip().split('\n') if tags_result.stdout.strip() else []

    # Check if working directory is clean
    diff_result = run("git status --porcelain", cwd=repo_path)
    is_clean = len(diff_result.stdout.strip()) == 0

    # Get ahead/behind counts
    ahead_behind = run(f"git rev-list --count {ref}..HEAD", cwd=repo_path)
    ahead = int(ahead_behind.stdout.strip()) if ahead_behind.stdout.strip() else 0

    return GitState(
        commits=commits,
        head_sha=head_sha,
        branch=branch,
        tags=tags,
        is_clean=is_clean,
        ahead_count=ahead
    )


def get_commit_info(repo_path: Path, commit_sha: str) -> Dict[str, str]:
    """Get detailed information about a commit."""
    result = run(f"git show --format=%H|%s|%an|%ad --date=short {commit_sha}", cwd=repo_path)
    line = result.stdout.strip().split('\n')[0]
    parts = line.split('|')

    return {
        'sha': parts[0],
        'subject': parts[1] if len(parts) > 1 else '',
        'author': parts[2] if len(parts) > 2 else '',
        'date': parts[3] if len(parts) > 3 else ''
    }


def count_commits_between(repo_path: Path, from_ref: str, to_ref: str) -> int:
    """Count commits between two references."""
    try:
        result = run(f"git rev-list --count {from_ref}..{to_ref}", cwd=repo_path)
        return int(result.stdout.strip())
    except subprocess.CalledProcessError:
        return 0


def validate_rebase_result(initial_enterprise_state: GitState, final_enterprise_state: GitState,
                          community_commits_added: int) -> TestResult:
    """Validate rebase operation results."""

    # Check that enterprise patches are preserved
    enterprise_patches_before = initial_enterprise_state.ahead_count
    enterprise_patches_after = final_enterprise_state.ahead_count

    # Should have same number of enterprise patches + new community commits
    expected_total_patches = enterprise_patches_before + community_commits_added

    patches_preserved = (enterprise_patches_after == expected_total_patches)
    clean_state = final_enterprise_state.is_clean
    head_moved = final_enterprise_state.head_sha != initial_enterprise_state.head_sha

    passed = patches_preserved and clean_state and (head_moved if community_commits_added > 0 else True)

    return TestResult(
        test_name="Rebase Validation",
        passed=passed,
        message=f"Patches preserved: {patches_preserved}, Clean: {clean_state}, Head moved: {head_moved}",
        expected={
            "enterprise_patches": enterprise_patches_before,
            "community_commits_added": community_commits_added,
            "total_expected": expected_total_patches
        },
        actual={
            "enterprise_patches_after": enterprise_patches_after,
            "is_clean": clean_state,
            "head_sha": final_enterprise_state.head_sha
        }
    )


def validate_squash_result(initial_enterprise_state: GitState, final_enterprise_state: GitState,
                          squashed_commits: int, expected_tag_pattern: str = "squash-") -> TestResult:
    """Validate squash operation results."""

    # Check that patches were squashed (should be fewer commits)
    expected_patches_after = initial_enterprise_state.ahead_count - squashed_commits + 1
    actual_patches_after = final_enterprise_state.ahead_count

    # Check for squash tag creation
    squash_tags = [tag for tag in final_enterprise_state.tags if tag.startswith(expected_tag_pattern)]
    tag_created = len(squash_tags) > 0

    # Check state is clean and head moved
    clean_state = final_enterprise_state.is_clean
    head_moved = final_enterprise_state.head_sha != initial_enterprise_state.head_sha

    patches_squashed = (actual_patches_after == expected_patches_after)

    passed = patches_squashed and clean_state and head_moved and tag_created

    return TestResult(
        test_name="Squash Validation",
        passed=passed,
        message=f"Patches squashed: {patches_squashed}, Tag created: {tag_created}, Clean: {clean_state}",
        expected={
            "patches_before": initial_enterprise_state.ahead_count,
            "squashed_commits": squashed_commits,
            "expected_patches_after": expected_patches_after
        },
        actual={
            "patches_after": actual_patches_after,
            "squash_tags": squash_tags,
            "is_clean": clean_state,
            "head_sha": final_enterprise_state.head_sha
        }
    )


def print_test_results(results: List[TestResult]) -> bool:
    """Print test results and return overall success."""
    print("\n" + "=" * 60)
    print("🧪 TEST RESULTS")
    print("=" * 60)

    passed_count = 0
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status}: {result.test_name}")
        print(f"   {result.message}")

        if not result.passed:
            if result.expected:
                print("   Expected:", result.expected)
            if result.actual:
                print("   Actual:", result.actual)

        if result.passed:
            passed_count += 1

    print(f"\n{'='*60}")
    print(f"Summary: {passed_count}/{len(results)} tests passed")
    print("="*60)

    return passed_count == len(results)


def setup_test_scenario() -> Tuple[GitState, GitState]:
    """Setup initial test scenario and return git states."""
    # Import setup function
    sys.path.insert(0, str(Path(__file__).parent))
    from setup_repos import setup_test_repos

    print("🔧 Setting up test repositories...")
    setup_test_repos()

    # Get initial states
    community_state = get_git_state(COMMUNITY_REPO)
    enterprise_state = get_git_state(ENTERPRISE_REPO)

    print(f"✅ Community: {len(community_state.commits)} commits")
    print(f"✅ Enterprise: {len(enterprise_state.commits)} commits ({enterprise_state.ahead_count} patches)")

    return community_state, enterprise_state