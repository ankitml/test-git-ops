#!/usr/bin/env python3
"""
Manual test runner for squash enterprise patches script.

This script helps you test different scenarios for squashing enterprise patches.
It creates multiple enterprise commits and then tests the squash functionality.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path("/tmp/test-community-sync")
ENTERPRISE_REPO = TEST_DIR / "enterprise-repo"


def run(cmd, cwd=None, check=True, capture_output=False):
    """Run shell command."""
    print(f"  $ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
    )
    if result.stdout and capture_output:
        print(f"    {result.stdout.strip()}")
    return result


def setup_squash_test_repos():
    """Create fresh test repositories specifically for squash testing.

    Creates:
    - community-origin (bare repo)
    - community-repo (with initial commits)
    - enterprise-origin (bare repo)
    - enterprise-repo (cloned from community, then with multiple enterprise patches)
    """
    print("🧹 Setting up fresh test repositories for squash testing...")

    # Clean up any existing test repos
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

    # Configure git
    run("git config user.name 'Community Bot'", cwd=community_repo)
    run("git config user.email 'community@test.com'", cwd=community_repo)

    # Initial commit
    (community_repo / "README.md").write_text("# Community Repository\n")
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

    # Add .gitignore
    (enterprise_repo / ".gitignore").write_text("scripts\n")
    run("git add .gitignore", cwd=enterprise_repo)
    run("git commit -m 'chore: ignore scripts symlink'", cwd=enterprise_repo)

    # Add multiple enterprise patches for squashing
    enterprise_patches = [
        ("enterprise-config.txt", "feat: add enterprise configuration"),
        ("enterprise-auth.txt", "feat: add enterprise authentication"),
        ("enterprise-logging.txt", "feat: add enterprise logging"),
        ("enterprise-monitoring.txt", "feat: add enterprise monitoring"),
        ("enterprise-security.txt", "feat: add enterprise security"),
    ]

    for filename, commit_msg in enterprise_patches:
        (enterprise_repo / filename).write_text(f"Enterprise {filename}\n")
        run(f"git add {filename}", cwd=enterprise_repo)
        run(f"git commit -m '{commit_msg}'", cwd=enterprise_repo)

    # Push to enterprise origin
    run("git push origin main", cwd=enterprise_repo)

    print("\n✅ Squash test repositories created successfully!")
    print(f"Community: {community_repo}")
    print(f"Enterprise: {enterprise_repo}")
    print("\nRepository state:")
    print(f"  Community: 4 commits (initial + 3 features)")
    print(f"  Enterprise: 9 commits (4 from community + 1 gitignore + 4 enterprise patches)")
    print("\nReady for squash testing! 🎯")


def show_git_state():
    """Show current git state of enterprise repo."""
    print("\n" + "=" * 60)
    print("📊 Current Git State")
    print("=" * 60)

    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found. Run setup_repos.py first.")
        return

    print("\n📝 Commit log (last 15 commits):")
    run("git log --oneline --graph --decorate -15", cwd=ENTERPRISE_REPO)

    print("\n🏷️  Tags:")
    run("git tag -l | head -10", cwd=ENTERPRISE_REPO, check=False)

    print("\n🔄 Community comparison:")
    run("git fetch community", cwd=ENTERPRISE_REPO, check=False)
    run("git log --oneline HEAD..community/main", cwd=ENTERPRISE_REPO, check=False)

    print("\n📊 Enterprise patch count:")
    run("git fetch origin", cwd=ENTERPRISE_REPO, check=False)
    result = run("git rev-list --count origin/main..HEAD 2>/dev/null || echo '0'",
                 cwd=ENTERPRISE_REPO, check=False, capture_output=True)
    if result.stdout:
        count = result.stdout.strip()
        print(f"   Enterprise patches on top of community: {count}")

    print("\n" + "=" * 60)


def add_enterprise_patches(count=3):
    """Add new enterprise patches to test squashing."""
    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found. Run setup_repos.py first.")
        return

    print(f"\n📝 Adding {count} new enterprise patches...")

    # Get current patch count for unique file names
    result = run("git rev-list --count HEAD", cwd=ENTERPRISE_REPO)
    start_num = int(result.stdout.strip()) + 1

    for i in range(count):
        patch_num = start_num + i
        filename = f"enterprise-patch-{patch_num}.txt"
        (ENTERPRISE_REPO / filename).write_text(f"Enterprise patch {patch_num}\n")
        run(f"git add {filename}", cwd=ENTERPRISE_REPO)
        run(f"git commit -m 'feat: enterprise patch {patch_num}'", cwd=ENTERPRISE_REPO)

    run("git push origin main", cwd=ENTERPRISE_REPO)
    print(f"\n✅ Added {count} enterprise patches")


def sync_community_first():
    """Sync community commits first, then add enterprise patches on top."""
    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found. Run setup_repos.py first.")
        return

    print("\n🔄 Syncing community commits first...")

    # Add some community commits
    print("📝 Adding 3 community commits...")
    test_base = Path(__file__).parent.parent
    result = run(f"python {test_base / 'src' / 'setup_repos.py'} add-commits 3", check=False)

    if result.returncode == 0:
        # Sync them to enterprise
        print("🔄 Syncing community commits to enterprise...")
        run("git fetch community", cwd=ENTERPRISE_REPO)
        scripts_dir = test_base / "scripts"
        rebase_script = scripts_dir / "rebase-community-batch.sh"

        cmd = f"{rebase_script} --skip-validation --max-commits 3"
        result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

        if result.returncode == 0:
            print("✅ Community commits synced successfully!")
        else:
            print("❌ Community sync failed!")

    show_git_state()


def test_squash_dry_run():
    """Test squash script with dry-run flag."""
    print("\n🔍 Testing squash script --dry-run...")

    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        print("❌ Squash script not found!")
        return

    cmd = f"{squash_script} --dry-run -m 'test: squashed enterprise patches'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    if result.returncode == 0:
        print("✅ Dry-run completed successfully!")
    else:
        print("❌ Dry-run failed!")


def test_squash_actual():
    """Test actual squash operation."""
    print("\n🔧 Testing actual squash operation...")

    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        print("❌ Squash script not found!")
        return

    cmd = f"{squash_script} -m 'test: squashed enterprise patches'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    if result.returncode == 0:
        print("✅ Squash completed successfully!")
    else:
        print("❌ Squash failed!")

    show_git_state()


def test_squash_force():
    """Test squash with --force flag (skip confirmation)."""
    print("\n⚡ Testing squash with --force flag...")

    scripts_dir = Path(__file__).parent.parent / "scripts"
    squash_script = scripts_dir / "squash-enterprise-patches.sh"

    if not squash_script.exists():
        print("❌ Squash script not found!")
        return

    cmd = f"{squash_script} --force -m 'test: forced squash of enterprise patches'"
    result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

    if result.returncode == 0:
        print("✅ Force squash completed successfully!")
    else:
        print("❌ Force squash failed!")

    show_git_state()


def reset_to_squashable_state():
    """Reset enterprise repo to have multiple patches for squashing."""
    print("\n🔄 Resetting to squashable state...")

    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found.")
        return

    # Find the common ancestor with community (should be the commit before enterprise patches)
    run("git fetch community", cwd=ENTERPRISE_REPO)
    run("git fetch origin", cwd=ENTERPRISE_REPO)

    # Reset to the initial state after setup (2 enterprise patches)
    print("📝 Resetting to base enterprise state + adding new patches...")

    # Get current HEAD
    result = run("git rev-parse HEAD", cwd=ENTERPRISE_REPO)
    current_head = result.stdout.strip()

    # Reset to just after initial setup (create 3 fresh patches)
    run("git reset --hard HEAD~3", cwd=ENTERPRISE_REPO, check=False)  # Remove last 3 patches if they exist

    # Add fresh patches for testing
    add_enterprise_patches(4)

    print("✅ Reset complete - ready for squash testing!")


def show_tag_details():
    """Show details of created squash tags."""
    print("\n🏷️  Squash Tag Details")
    print("=" * 40)

    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found.")
        return

    # Show recent tags
    result = run("git tag -l 'squash-*' | sort -r | head -5",
                 cwd=ENTERPRISE_REPO, check=False)

    if result.returncode == 0 and result.stdout:
        tags = result.stdout.strip().split('\n')
        for tag in tags[:3]:  # Show details for up to 3 most recent tags
            if tag.strip():
                print(f"\n📋 Tag: {tag}")
                run(f"git show {tag} --stat", cwd=ENTERPRISE_REPO)
    else:
        print("No squash tags found.")


def main():
    """Interactive squash test runner."""
    print("🧪 Enterprise Squash Test Runner")
    print("=" * 60)

    # Get script directory
    test_base = Path(__file__).parent.parent
    scripts_dir = test_base / "scripts"

    if not scripts_dir.exists():
        print("\n❌ Scripts not found!")
        print("\nRun this first:")
        print(f"  python src/copy_scripts.py /path/to/your/enterprise-repo")
        sys.exit(1)

    while True:
        print("\n" + "=" * 60)
        print("📋 Squash Test Options")
        print("=" * 60)
        print("1. Setup fresh test repos (wipe existing)")
        print("2. Show current git state")
        print("3. Add 3 enterprise patches (for squashing)")
        print("4. Add 5 enterprise patches (for squashing)")
        print("5. Sync community first, then add patches")
        print("6. Reset to squashable state (4 patches)")
        print("7. Test squash --dry-run")
        print("8. Test actual squash operation")
        print("9. Test squash with --force")
        print("10. Show squash tag details")
        print("11. Exit")
        print("=" * 60)

        choice = input("\nSelect option (1-11): ").strip()

        if choice == "1":
            setup_squash_test_repos()

        elif choice == "2":
            show_git_state()

        elif choice == "3":
            add_enterprise_patches(3)
            show_git_state()

        elif choice == "4":
            add_enterprise_patches(5)
            show_git_state()

        elif choice == "5":
            sync_community_first()

        elif choice == "6":
            reset_to_squashable_state()
            show_git_state()

        elif choice == "7":
            test_squash_dry_run()

        elif choice == "8":
            test_squash_actual()

        elif choice == "9":
            test_squash_force()

        elif choice == "10":
            show_tag_details()

        elif choice == "11":
            print("\n👋 Exiting...")
            break

        else:
            print("\n❌ Invalid option. Please try again.")


if __name__ == "__main__":
    main()