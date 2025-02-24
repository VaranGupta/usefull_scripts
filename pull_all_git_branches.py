#!/usr/bin/env python3
"""
Git Branch Puller and Error Handler Script
============================================

Description:
-------------
This script automates the process of fetching remote branches from a Git repository,
checking out each branch (without upstream tracking), and pulling the latest changes.
It is designed to work within a specified working directory (DEFAULT_CWD) and includes
error handling with a timeout for each Git command.

Features:
---------
- Fetches all remote branches.
- Checks out each branch from the remote repository.
- Verifies if the branch is behind its remote counterpart; if so, it attempts to pull updates.
- If a pull fails, logs the branch name and error to a log file (LOG_FILE).
- Prompts the user to retry or skip the pull if an error occurs.
- Uses a timeout (DEFAULT_TIMEOUT) for Git commands to avoid hanging indefinitely.

User Guide:
-----------
1. **Configuration:**
   - Set the `DEFAULT_CWD` variable to the path of your Git repository.
   - Adjust `DEFAULT_TIMEOUT` (in seconds) if you need a longer or shorter timeout.

2. **Usage:**
   - Run the script from the command line:
     ```
     ./your_script_name.py
     ```
   - The script will automatically fetch all remote branches.
   - For each branch:
     - It will check out the branch.
     - It will check if the branch is behind its remote version. If not, it will skip pulling.
     - If updates are available, it will attempt to pull them.
     - In case of a pull error, the error is logged to `pull_errors.log` and you will be prompted:
       - **y**: Retry the pull.
       - **n**: Skip pulling for that branch.
       - Note: Reccomendation is to manually resolve any error and skip pulling 
       
3. **Error Logging:**
   - Any pull errors (including retry failures) are appended to the file specified by `LOG_FILE`.
   - Review this file later to see which branches encountered issues.

4. **Dependencies:**
   - Python 3.x is required.
   - Git must be installed and available in the system’s PATH.
   
5. **Note:**
   - This script does not set up upstream tracking on local branches.
   - Ensure you run the script in an environment where the repository exists at the specified `DEFAULT_CWD`.

Author: Varan Gupta
Date: 24/02/2025
"""

import subprocess
import sys
import re

LOG_FILE = "pull_errors.log"
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_CWD = "."  # location of the repo


def run_command(cmd, cwd=DEFAULT_CWD, timeout=DEFAULT_TIMEOUT):
    """
    Runs a command using subprocess with a specified timeout.
    Returns the stdout output if successful; otherwise raises an exception.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise Exception(f"Command '{' '.join(cmd)}' timed out after {timeout} seconds.")
    except subprocess.CalledProcessError as e:
        raise Exception(e.stderr.strip())


def log_pull_error(branch, error_message, log_file=LOG_FILE):
    """
    Append the branch name and error message to a log file.
    """
    try:
        with open(log_file, "a") as f:
            f.write(f"Pull error on branch '{branch}': {error_message}\n")
    except Exception as ex:
        print("Error logging pull error:", ex)


def is_git_repo():
    """
    Checks if the current directory is inside a git repository.
    """
    try:
        output = run_command(["git", "rev-parse", "--is-inside-work-tree"])
        return output.lower() == "true"
    except Exception:
        return False


def get_remote_branches():
    """
    Returns a list of remote branch names (without the 'origin/' prefix).
    """
    output = run_command(["git", "branch", "-r"])
    branches = []
    for line in output.splitlines():
        line = line.strip()
        if "->" in line:  # skip symbolic refs like HEAD -> origin/...
            continue
        m = re.match(r"origin/(.+)", line)
        if m:
            branches.append(m.group(1))
        else:
            branches.append(line)
    return branches


def get_local_branches():
    """
    Returns a list of local branch names.
    """
    output = run_command(["git", "branch"])
    branches = []
    for line in output.splitlines():
        branch = line.strip().lstrip("*").strip()
        branches.append(branch)
    return branches


def branch_needs_pull(branch):
    """
    Checks if the local branch is behind its remote counterpart.
    Returns True if there are new commits in origin/branch.
    """
    try:
        count = run_command(
            ["git", "rev-list", "--count", f"{branch}..origin/{branch}"]
        )
        return int(count) > 0
    except Exception as e:
        print(f"  Could not compare branch '{branch}' with remote: {e}")
        return True  # if in doubt, assume pull is needed


def main():
    if not is_git_repo():
        print("Error: This directory is not a Git repository.")
        sys.exit(1)

    print("Fetching all remote branches...")
    try:
        run_command(["git", "fetch", "--all"])
    except Exception:
        print("Failed to fetch remote branches. Exiting.")
        sys.exit(1)

    try:
        remote_branches = get_remote_branches()
        if not remote_branches:
            print("No remote branches found.")
            sys.exit(0)
    except Exception:
        print("Failed to retrieve remote branches.")
        sys.exit(1)

    for branch in remote_branches:
        print(f"\nProcessing branch '{branch}':")
        try:
            print("Checking out branch...")
            run_command(["git", "checkout", branch])
        except Exception as e:
            print(f"  Error checking out branch '{branch}': {e}")
            continue

        # Check if branch is up to date
        try:
            if not branch_needs_pull(branch):
                print("  Branch is already up to date. Skipping pull.")
                continue
        except Exception as e:
            print(f"  Could not determine status for branch '{branch}': {e}")
            # Continue with pull attempt

        try:
            print("  Pulling latest changes...")
            run_command(["git", "pull"])
        except Exception as e:
            error_msg = str(e)
            print(f"  Error pulling branch '{branch}': {error_msg}")
            log_pull_error(branch, error_msg)
            while True:
                user_input = (
                    input(f"Pull error on branch '{branch}'. Try again? (y/n): ")
                    .strip()
                    .lower()
                )
                if user_input == "y":
                    try:
                        print("  Retrying pull...")
                        run_command(["git", "pull"])
                        print("  Pull succeeded.")
                        break  # exit retry loop on success
                    except Exception as retry_e:
                        error_msg_retry = str(retry_e)
                        print(f"  Retry failed: {error_msg_retry}")
                        log_pull_error(branch, f"Retry: {error_msg_retry}")
                        continue
                elif user_input == "n":
                    print(f"  Skipping pull for branch '{branch}'.")
                    break
                else:
                    print("  Please enter 'y' (yes) or 'n' (no).")
                    continue

    print("\nAll branches processed.")


if __name__ == "__main__":
    main()
