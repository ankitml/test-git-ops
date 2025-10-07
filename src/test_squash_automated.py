#!/usr/bin/env python3
"""
Simple manual test of squash script with known state.

Setup:
- Community: 3 commits (initial + 2 features)
- Enterprise: Same 3 community commits + 3 enterprise patches
- Test: Squash the 3 enterprise patches into 1 commit
"""

import subprocess
import sys
from pathlib import Path

TEST_DIR = Path("/tmp/test-community-sync")
ENTERPRISE_REPO = TEST_DIR / "enterprise-repo"


def run(cmd, cwd=None, check=True):
    """Run shell command."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, capture_output=True, text=True)
    if result.stdout:
        print(f"    {result.stdout.strip()}")
    return result


def setup_simple_test():
    """Create simple test scenario: 3 community + 3 enterprise commits."""
    print("🧹 Setting up simple test scenario...")

    # Clean up
    if TEST_DIR.exists():
        subprocess.run(f"rm -rf {TEST_DIR}", shell=True)
    TEST_DIR.mkdir(parents=True)

    print("\n📦 Creating community repository...")
    community_origin = TEST_DIR / "community-origin"
    community_repo = TEST_DIR / "community-repo"

    # Create community repo with exactly 3 commits
    run(f"git init --bare {community_origin}")
    run(f"git clone {community_origin} {community_repo}")
    run("git config user.name 'Community Bot'", cwd=community_repo)
    run("git config user.email 'community@test.com'", cwd=community_repo)

    # Commit 1: Initial
    (community_repo / "README.md").write_text("# Community\n")
    run("git add README.md", cwd=community_repo)
    run("git commit -m 'initial: add README'", cwd=community_repo)

    # Commit 2: Feature 1
    (community_repo / "feature1.txt").write_text("Feature 1\n")
    run("git add feature1.txt", cwd=community_repo)
    run("git commit -m 'feat: add feature 1'", cwd=community_repo)

    # Commit 3: Feature 2
    (community_repo / "feature2.txt").write_text("Feature 2\n")
    run("git add feature2.txt", cwd=community_repo)
    run("git commit -m 'feat: add feature 2'", cwd=community_repo)

    run("git push origin main", cwd=community_repo)

    print("\n📦 Creating enterprise repository...")
    enterprise_origin = TEST_DIR / "enterprise-origin"
    enterprise_repo = TEST_DIR / "enterprise-repo"

    # Create enterprise repo from community
    run(f"git init --bare {enterprise_origin}")
    run(f"git clone {community_origin} {enterprise_repo}")
    run(f"git remote set-url origin {enterprise_origin}", cwd=enterprise_repo)
    run("git config user.name 'Enterprise Bot'", cwd=enterprise_repo)
    run("git config user.email 'enterprise@test.com'", cwd=enterprise_repo)
    run(f"git remote add community {community_origin}", cwd=enterprise_repo)
    run("git fetch community", cwd=enterprise_repo)

    # Add 3 enterprise patches
    (enterprise_repo / "enterprise1.txt").write_text("Enterprise 1\n")
    run("git add enterprise1.txt", cwd=enterprise_repo)
    run("git commit -m 'feat: enterprise patch 1'", cwd=enterprise_repo)

    (enterprise_repo / "enterprise2.txt").write_text("Enterprise 2\n")
    run("git add enterprise2.txt", cwd=enterprise_repo)
    run("git commit -m 'feat: enterprise patch 2'", cwd=enterprise_repo)

    (enterprise_repo / "enterprise3.txt").write_text("Enterprise 3\n")
    run("git add enterprise3.txt", cwd=enterprise_repo)
    run("git commit -m 'feat: enterprise patch 3'", cwd=enterprise_repo)

    run("git push origin main", cwd=enterprise_repo)

    print("\n✅ Setup complete!")
    print("Community: 3 commits")
    print("Enterprise: 6 commits (3 community + 3 enterprise)")

    return enterprise_repo


def test_squash(enterprise_repo):
    """Test the squash script."""
    print("\n🔧 Testing squash script...")

    # Get state before
    print("\n📊 State before squash:")
    result = run("git log --oneline -10", cwd=enterprise_repo)

    # Find common ancestor and show enterprise vs community
    run("git fetch community", cwd=enterprise_repo)
    common_ancestor = run("git merge-base HEAD community/main", cwd=enterprise_repo).stdout.strip()

    print(f"\n🔍 Common ancestor: {common_ancestor[:8]}")
    print("\n📋 Enterprise patches (commits after common ancestor):")
    enterprise_commits = run(f"git log --oneline {common_ancestor}..HEAD", cwd=enterprise_repo).stdout.strip()
    if enterprise_commits:
        for line in enterprise_commits.split('\n'):
            print(f"   • {line}")

    enterprise_patches_before = run(f"git rev-list --count {common_ancestor}..HEAD", cwd=enterprise_repo).stdout.strip()
    print(f"\n🎯 Enterprise patches count before: {enterprise_patches_before}")

    # Run squash script
    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        print("❌ Squash script not found!")
        return False

    cmd = f"{squash_script} --force -m 'test: squashed enterprise patches'"
    result = run(cmd, cwd=enterprise_repo, check=False)

    if result.returncode != 0:
        print(f"❌ Squash script failed: {result.stderr}")
        return False

    # Get state after
    print("\n📊 State after squash:")
    result = run("git log --oneline -10", cwd=enterprise_repo)

    # Find common ancestor after squash and show new state
    run("git fetch community", cwd=enterprise_repo)
    common_ancestor_after = run("git merge-base HEAD community/main", cwd=enterprise_repo).stdout.strip()

    print(f"\n🔍 Common ancestor after: {common_ancestor_after[:8]}")
    print("\n📋 Enterprise patches after squashing:")
    enterprise_commits_after = run(f"git log --oneline {common_ancestor_after}..HEAD", cwd=enterprise_repo).stdout.strip()
    if enterprise_commits_after:
        for line in enterprise_commits_after.split('\n'):
            print(f"   • {line}")

    enterprise_patches_after = run(f"git rev-list --count {common_ancestor_after}..HEAD", cwd=enterprise_repo).stdout.strip()
    print(f"\n🎯 Enterprise patches count after: {enterprise_patches_after}")

    # Check tags
    tags = run("git tag -l", cwd=enterprise_repo).stdout.strip()
    print(f"\n🏷️  Tags created: {tags}")

    # Validate: Should have 1 enterprise patch after squashing 3
    expected_patches = "1"  # 3 patches squashed into 1
    success = enterprise_patches_after == expected_patches

    print(f"\n{'✅' if success else '❌'} Test result:")
    print(f"  Expected: 3 enterprise patches → 1 squashed patch")
    print(f"  Actual: {enterprise_patches_before} enterprise patches → {enterprise_patches_after} patches")

    return success


def main():
    print("🧪 Simple Squash Test")
    print("=" * 50)

    enterprise_repo = setup_simple_test()
    success = test_squash(enterprise_repo)

    if success:
        print("\n🎉 Squash test PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Squash test FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()