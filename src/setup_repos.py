#!/usr/bin/env python3
"""
Setup test repositories for community sync testing.

Creates:
- community-origin (bare repo, acts as remote)
- community-repo (local clone)
- enterprise-origin (bare repo, acts as remote)
- enterprise-repo (local clone, rebased on community with enterprise patches)
"""

import os
import shutil
import subprocess
from pathlib import Path

TEST_DIR = Path("/tmp/test-community-sync")


def run(cmd, cwd=None, check=True):
    """Run shell command and return output."""
    print(f"  $ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )
    if result.stdout:
        print(f"    {result.stdout.strip()}")
    return result


def setup_test_repos():
    """Create test repository structure."""
    print("🧹 Cleaning up old test repos...")
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True)

    print("\n📦 Creating community repository...")
    community_origin = TEST_DIR / "community-origin"
    community_repo = TEST_DIR / "community-repo"

    # Create bare origin repo
    run(f"git init --bare {community_origin}")

    # Create and populate community repo
    run(f"git clone {community_origin} {community_repo}")

    # Initial commit
    run("git config user.name 'Community Bot'", cwd=community_repo)
    run("git config user.email 'community@test.com'", cwd=community_repo)

    (community_repo / "README.md").write_text("# Community Repo\n")
    run("git add README.md", cwd=community_repo)
    run("git commit -m 'Initial commit'", cwd=community_repo)
    run("git push origin main", cwd=community_repo)

    # Add some community commits
    for i in range(1, 4):
        (community_repo / f"feature{i}.txt").write_text(f"Feature {i}\n")
        run(f"git add feature{i}.txt", cwd=community_repo)
        run(f"git commit -m 'feat: add feature {i}'", cwd=community_repo)

    run("git push origin main", cwd=community_repo)

    print("\n📦 Creating enterprise repository...")
    enterprise_origin = TEST_DIR / "enterprise-origin"
    enterprise_repo = TEST_DIR / "enterprise-repo"

    # Create bare origin repo
    run(f"git init --bare {enterprise_origin}")

    # Clone from community to start with same history
    run(f"git clone {community_origin} {enterprise_repo}")

    # Repoint origin to enterprise-origin
    run(f"git remote set-url origin {enterprise_origin}", cwd=enterprise_repo)

    # Configure git
    run("git config user.name 'Enterprise Bot'", cwd=enterprise_repo)
    run("git config user.email 'enterprise@test.com'", cwd=enterprise_repo)

    # Add community remote
    run(f"git remote add community {community_origin}", cwd=enterprise_repo)
    run("git fetch community", cwd=enterprise_repo)

    # Add .gitignore to ignore scripts symlink that will be added later
    (enterprise_repo / ".gitignore").write_text("scripts\n")
    run("git add .gitignore", cwd=enterprise_repo)
    run("git commit -m 'chore: ignore scripts symlink'", cwd=enterprise_repo)

    # Add enterprise patches on top
    (enterprise_repo / "enterprise-config.txt").write_text("Enterprise config\n")
    run("git add enterprise-config.txt", cwd=enterprise_repo)
    run("git commit -m 'feat: add enterprise configuration'", cwd=enterprise_repo)

    (enterprise_repo / "enterprise-auth.txt").write_text("Enterprise auth\n")
    run("git add enterprise-auth.txt", cwd=enterprise_repo)
    run("git commit -m 'feat: add enterprise authentication'", cwd=enterprise_repo)

    # Push to enterprise origin
    run("git push origin main", cwd=enterprise_repo)

    # Copy scripts to enterprise repo using ENTERPRISE_REPO from environment
    import os
    enterprise_repo_source = os.environ.get('ENTERPRISE_REPO')
    if enterprise_repo_source:
        scripts_dir = Path(enterprise_repo_source) / "scripts"
        if scripts_dir.exists():
            enterprise_scripts = enterprise_repo / "scripts"
            if enterprise_scripts.exists():
                shutil.rmtree(enterprise_scripts)
            shutil.copytree(scripts_dir, enterprise_scripts)
            # Make scripts executable
            for script_file in enterprise_scripts.glob("*.sh"):
                script_file.chmod(0o755)
            print("✅ Scripts copied to enterprise test repo")
        else:
            print(f"⚠️  Scripts directory not found at {scripts_dir}")
    else:
        print("⚠️  ENTERPRISE_REPO environment variable not set")

    print("\n✅ Test repositories created successfully!")
    print(f"\nCommunity repo: {community_repo}")
    print(f"Enterprise repo: {enterprise_repo}")
    print("\nCurrent state:")
    print(f"  Community: 4 commits (initial + 3 features)")
    print(f"  Enterprise: 7 commits (same 4 from community + gitignore + 2 enterprise patches)")
    print("\nNext steps:")
    print(f"  1. Add more commits to community: cd {community_repo}")
    print(f"  2. Test sync from enterprise: cd {enterprise_repo}")
    print(f"  3. Run sync script with test repos")


def add_community_commits(count=3):
    """Add new commits to community repo for testing sync."""
    community_repo = TEST_DIR / "community-repo"

    if not community_repo.exists():
        print("❌ Community repo not found. Run setup_repos() first.")
        return

    print(f"\n📝 Adding {count} new commits to community repo...")

    # Get current commit count for unique file names
    result = run("git rev-list --count HEAD", cwd=community_repo)
    start_num = int(result.stdout.strip()) + 1

    for i in range(count):
        file_num = start_num + i
        filename = f"update{file_num}.txt"
        (community_repo / filename).write_text(f"Update {file_num}\n")
        run(f"git add {filename}", cwd=community_repo)
        run(f"git commit -m 'feat: add update {file_num}'", cwd=community_repo)

    run("git push origin main", cwd=community_repo)

    print(f"\n✅ Added {count} commits to community repo")
    print("\nTo sync to enterprise:")
    print(f"  cd {TEST_DIR / 'enterprise-repo'}")
    print(f"  git fetch community")
    print(f"  # Run your sync script here")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "add-commits":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        add_community_commits(count)
    else:
        setup_test_repos()
