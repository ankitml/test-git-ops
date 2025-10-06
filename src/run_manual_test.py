#!/usr/bin/env python3
"""
Manual test runner for community sync scripts.

This script helps you quickly test different scenarios interactively.
"""

import subprocess
import sys
from pathlib import Path

TEST_DIR = Path("/tmp/test-community-sync")
ENTERPRISE_REPO = TEST_DIR / "enterprise-repo"


def run(cmd, cwd=None, check=True):
    """Run shell command."""
    print(f"\n💻 Running: {cmd}\n")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        check=check,
    )
    return result


def show_git_state():
    """Show current git state of enterprise repo."""
    print("\n" + "=" * 60)
    print("📊 Current Git State")
    print("=" * 60)

    if not ENTERPRISE_REPO.exists():
        print("❌ Enterprise repo not found. Run setup_repos.py first.")
        return

    print("\n📝 Commit log (last 10 commits):")
    run("git log --oneline --graph --decorate -10", cwd=ENTERPRISE_REPO)

    print("\n🔄 Remote comparison:")
    run("git fetch community", cwd=ENTERPRISE_REPO, check=False)
    run("git log --oneline HEAD..community/main", cwd=ENTERPRISE_REPO, check=False)

    print("\n" + "=" * 60)


def main():
    """Interactive test runner."""
    print("🧪 Community Sync Manual Test Runner")
    print("=" * 60)

    if not ENTERPRISE_REPO.exists():
        print("\n❌ Test repos not found!")
        print("\nRun this first:")
        print("  python src/setup_repos.py")
        sys.exit(1)

    # Get script directory
    test_base = Path(__file__).parent.parent
    scripts_dir = test_base / "scripts"

    if not scripts_dir.exists():
        print("\n❌ Scripts not found!")
        print("\nRun this first:")
        print(f"  python src/copy_scripts.py /path/to/your/enterprise-repo")
        sys.exit(1)

    rebase_script = scripts_dir / "rebase-community-batch.sh"

    while True:
        print("\n" + "=" * 60)
        print("📋 Test Options")
        print("=" * 60)
        print("1. Show current git state")
        print("2. Add 1 commit to community repo")
        print("3. Add 3 commits to community repo")
        print("4. Add 5 commits to community repo")
        print("5. Sync 1 commit (with --skip-validation)")
        print("6. Sync 3 commits (with --skip-validation)")
        print("7. Sync 5 commits (with --skip-validation)")
        print("8. Create a conflicting commit (for testing conflicts)")
        print("9. Exit")
        print("=" * 60)

        choice = input("\nSelect option (1-9): ").strip()

        if choice == "1":
            show_git_state()

        elif choice in ["2", "3", "4"]:
            count = int(choice)
            print(f"\n📝 Adding {count} commit(s) to community repo...")
            result = run(
                f"python {test_base / 'src' / 'setup_repos.py'} add-commits {count}",
                check=False,
            )
            if result.returncode == 0:
                show_git_state()

        elif choice in ["5", "6", "7"]:
            max_commits = {"5": 1, "6": 3, "7": 5}[choice]
            print(f"\n🔄 Syncing up to {max_commits} commit(s)...")

            # Fetch first
            run("git fetch community", cwd=ENTERPRISE_REPO)

            # Run sync with skip-validation
            cmd = f"{rebase_script} --skip-validation --max-commits {max_commits}"
            result = run(cmd, cwd=ENTERPRISE_REPO, check=False)

            if result.returncode == 0:
                print("\n✅ Sync completed successfully!")
            else:
                print("\n❌ Sync failed! Check output above.")

            show_git_state()

        elif choice == "8":
            print("\n⚠️  Creating conflicting commit in enterprise repo...")
            # This creates a commit that will likely conflict with community changes
            conflict_file = ENTERPRISE_REPO / "README.md"
            conflict_file.write_text("# Conflicting change from enterprise\n")
            run("git add README.md", cwd=ENTERPRISE_REPO)
            run("git commit -m 'enterprise: conflicting change'", cwd=ENTERPRISE_REPO)
            print("\n✅ Conflicting commit created!")
            show_git_state()

        elif choice == "9":
            print("\n👋 Exiting...")
            break

        else:
            print("\n❌ Invalid option. Please try again.")


if __name__ == "__main__":
    main()
