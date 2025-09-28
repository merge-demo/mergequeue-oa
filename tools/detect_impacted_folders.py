#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def get_git_status_files() -> Set[str]:
    """
    Get all files that have been modified, added, deleted, or are untracked according to git status.
    Returns a set of file paths relative to the repository root.
    """
    try:
        # Get git status output for modified, added, deleted, and untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )

        files = set()
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            status_code = line[:2]
            # Untracked files (??)
            if status_code == "??":
                file_path = line[2:]
                files.add(file_path)
            else:
                # Tracked files: status code is two chars, then a space, then the path
                # e.g. ' M bazel/delta/delta.txt'
                file_path = line[2:]
                if any(code in status_code for code in ["M", "A", "D", "R"]):
                    files.add(file_path)
        return files
    except subprocess.CalledProcessError as e:
        print(f"Error running git status: {e}", file=sys.stderr)
        return set()
    except FileNotFoundError:
        print(
            "Error: git command not found. Make sure git is installed and in PATH.",
            file=sys.stderr,
        )
        return set()


def get_folders_from_files(files: Set[str]) -> Set[str]:
    """
    Extract the deepest folder from each file path. If the file is at root, use '/'.
    Returns a set of folder paths relative to the repository root.
    """
    folders = set()
    for file_path in files:
        path = Path(file_path)
        if path.parent == Path("."):
            folders.add("/")
        else:
            folders.add(str(path.parent))
    return folders


def write_impacted_targets_json(
    folders: Set[str],
    output_file: str = "impacted_targets_json_tmp",
    verbose: bool = True,
):
    """
    Write the list of impacted folders to a JSON file in the expected format.
    """
    # Convert to sorted list for consistent output
    folder_list = sorted(list(folders))

    try:
        # Write as JSON array
        with open(output_file, "w") as f:
            json.dump(folder_list, f)

        if verbose:
            print(f"Wrote {len(folder_list)} impacted folders to {output_file}")
            if folder_list:
                print("Impacted folders:")
                for folder in folder_list:
                    print(f"  - {folder}")
            else:
                print("No impacted folders found")

    except IOError as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to detect impacted folders from git status and write to JSON file.
    """
    parser = argparse.ArgumentParser(
        description="Detect impacted folders from git status changes and write to JSON file"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="impacted_targets_json_tmp",
        help="Output file path (default: impacted_targets_json_tmp)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress verbose output"
    )
    parser.add_argument(
        "--check-git-repo",
        action="store_true",
        help="Check if current directory is a git repository",
    )

    args = parser.parse_args()

    # Check if we're in a git repository
    if args.check_git_repo:
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            print("Error: Not in a git repository", file=sys.stderr)
            sys.exit(1)

    if not args.quiet:
        print("Analyzing git status for impacted folders...")

    # Get files that have been modified
    modified_files = get_git_status_files()

    if not modified_files:
        if not args.quiet:
            print("No modified files found in git status")
        write_impacted_targets_json(set(), args.output, not args.quiet)
        return

    if not args.quiet:
        print(f"Found {len(modified_files)} modified files")

    # Extract folder paths from file paths
    impacted_folders = get_folders_from_files(modified_files)

    # Write to JSON file
    write_impacted_targets_json(impacted_folders, args.output, not args.quiet)


if __name__ == "__main__":
    main()
