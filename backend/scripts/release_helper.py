"""
Release Helper Script.
Validates the version tags against the declared versions in the codebase
and extracts the changelog section for GitHub Release notes.
"""

import json
import os
import re
import subprocess
import sys

# Ensure UTF-8 console output on Windows/etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    # 1. Get the tag from environment or argument
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if len(sys.argv) > 1:
        tag = sys.argv[1]

    if not tag:
        print("ERROR: No tag name provided (GITHUB_REF_NAME environment variable or command line argument).")
        sys.exit(1)

    print(f"Validating release for tag: {tag}")

    # Ensure tag starts with 'v'
    if not tag.startswith("v"):
        print(f"ERROR: Tag '{tag}' must start with 'v' (e.g. v1.0.0).")
        sys.exit(1)

    version = tag[1:]  # strip 'v' prefix, e.g., '0.9.6-beta'
    print(f"Inferred version: {version}")

    # Paths relative to repository root
    repo_root = os.getcwd()
    package_json_path = os.path.join(repo_root, "frontend", "package.json")
    project_state_path = os.path.join(repo_root, "PROJECT_STATE.md")
    changelog_path = os.path.join(repo_root, "CHANGELOG.md")

    errors = []

    # Check if we are in a Git repository
    is_git = os.path.exists(os.path.join(repo_root, ".git"))

    if is_git:
        # 2. Check if git tag exists in history
        try:
            res = subprocess.run(["git", "rev-parse", tag], capture_output=True, text=True)
            if res.returncode != 0:
                errors.append(f"Git tag '{tag}' does not exist in the repository's history.")
            else:
                print("✓ Git tag exists in history.")
        except Exception as e:
            print(f"Warning: Could not run 'git rev-parse' to verify tag existence: {e}")

        # 3. Check if git working tree is clean
        try:
            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if res.returncode == 0:
                status_output = res.stdout.strip()
                if status_output:
                    errors.append(f"Git working tree is dirty. Uncommitted changes found:\n{status_output}")
                else:
                    print("✓ Git working tree is clean.")
            else:
                errors.append(f"Failed to check git status (exit code {res.returncode}): {res.stderr}")
        except Exception as e:
            print(f"Warning: Could not run 'git status' to check working tree cleanliness: {e}")
    else:
        print("Skipping Git tag and working tree checks (not in a Git repository).")

    # 4. Validate package.json
    if not os.path.exists(package_json_path):
        errors.append(f"Missing frontend/package.json at: {package_json_path}")
    else:
        try:
            with open(package_json_path, encoding="utf-8") as f:
                pkg_data = json.load(f)
            pkg_version = pkg_data.get("version")
            if pkg_version != version:
                errors.append(f"Version mismatch in frontend/package.json: expected '{version}', found '{pkg_version}'")
            else:
                print("✓ frontend/package.json version matches.")
        except Exception as e:
            errors.append(f"Failed to read frontend/package.json: {e}")

    # 5. Validate PROJECT_STATE.md
    if not os.path.exists(project_state_path):
        errors.append(f"Missing PROJECT_STATE.md at: {project_state_path}")
    else:
        try:
            with open(project_state_path, encoding="utf-8") as f:
                state_content = f.read()
            match = re.search(r"##\s+Version\s*\n\s*(v?\d+\.\d+\.\d+[-\w]*)", state_content, re.IGNORECASE)
            if not match:
                errors.append("Could not find version entry under '## Version' heading in PROJECT_STATE.md")
            else:
                state_version = match.group(1).strip()
                if state_version != tag and state_version != version:
                    errors.append(
                        f"Version mismatch in PROJECT_STATE.md: expected '{tag}' or '{version}', found '{state_version}'"
                    )
                else:
                    print("✓ PROJECT_STATE.md version matches.")
        except Exception as e:
            errors.append(f"Failed to read PROJECT_STATE.md: {e}")

    # 6. Validate and Extract CHANGELOG.md
    if not os.path.exists(changelog_path):
        errors.append(f"Missing CHANGELOG.md at: {changelog_path}")
    else:
        try:
            with open(changelog_path, encoding="utf-8") as f:
                changelog_content = f.read()

            header_pattern = r"##\s+\[?v?" + re.escape(version) + r"\]?.*"
            matches = list(re.finditer(header_pattern, changelog_content))
            if not matches:
                errors.append(f"Could not find a '##' header for version '{version}' or '{tag}' in CHANGELOG.md")
            else:
                print("✓ CHANGELOG.md contains header for this version.")
                start_idx = matches[0].end()
                next_header_match = re.search(r"\n##\s+", changelog_content[start_idx:])
                if next_header_match:
                    end_idx = start_idx + next_header_match.start()
                else:
                    end_idx = len(changelog_content)

                release_notes = changelog_content[start_idx:end_idx].strip()
                if not release_notes:
                    errors.append(f"Changelog section for version '{version}' is empty.")
                else:
                    release_notes_file = os.path.join(repo_root, "release_notes.txt")
                    with open(release_notes_file, "w", encoding="utf-8") as rf:
                        rf.write(release_notes)
                    print(f"✓ Extracted release notes written to: {release_notes_file}")
        except Exception as e:
            errors.append(f"Failed to process CHANGELOG.md: {e}")

    # 7. Output results
    if errors:
        print("\n❌ RELEASE VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n✅ RELEASE VALIDATION PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
