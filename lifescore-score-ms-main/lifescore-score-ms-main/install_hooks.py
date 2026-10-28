"""
This script installs Git hooks for the repository.
"""

import os
import subprocess
import sys
import shutil


def set_hooks_path():
    """Set the Git hooks directory to the shared hooks folder."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    hooks_dir = os.path.join(repo_root, "hooks")

    # Set core.hooksPath to the hooks directory
    try:
        subprocess.run(["git", "config", "core.hooksPath", hooks_dir], check=True)
        print(f"Git hooks directory set to: {hooks_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error setting core.hooksPath: {e}")
        sys.exit(1)


def install_pre_commit():
    """Ensure the pre-commit framework is installed and its hook is copied to hooks/."""
    print("Checking for pre-commit...")
    try:
        # Check if pre-commit is installed
        subprocess.run(
            ["pre-commit", "--version"], check=True, stdout=subprocess.DEVNULL
        )
    except FileNotFoundError:
        print("pre-commit is not installed. Installing it now...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pre-commit"], check=True
            )
            print("pre-commit installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing pre-commit: {e}")
            sys.exit(1)

    # Temporarily unset core.hooksPath to allow pre-commit to install
    print("Temporarily unsetting core.hooksPath for pre-commit installation...")
    try:
        subprocess.run(["git", "config", "--unset", "core.hooksPath"], check=True)
    except subprocess.CalledProcessError:
        print("core.hooksPath was not set. Skipping unset step.")

    # Install pre-commit hooks
    print("Installing pre-commit framework hooks...")
    try:
        subprocess.run(["pre-commit", "install"], check=True)
        print("Pre-commit framework hooks installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing pre-commit hooks: {e}")
        sys.exit(1)

    # Copy the pre-commit hook to the custom hooks directory
    repo_root = os.path.dirname(os.path.abspath(__file__))
    hooks_dir = os.path.join(repo_root, "hooks")
    pre_commit_hook_src = os.path.join(repo_root, ".git", "hooks", "pre-commit")
    pre_commit_hook_dest = os.path.join(hooks_dir, "pre-commit")

    if os.path.exists(pre_commit_hook_src):
        shutil.copy(pre_commit_hook_src, pre_commit_hook_dest)
        os.chmod(pre_commit_hook_dest, 0o755)
        print(f"Copied pre-commit hook to {hooks_dir}/pre-commit")

    # Restore core.hooksPath
    set_hooks_path()


if __name__ == "__main__":
    print("Setting up Git hooks...")
    set_hooks_path()
    install_pre_commit()
    print("All hooks installed successfully.")
