#!/usr/bin/env python3
"""
Script to update project statistics in README.md

This script gathers real-time statistics about the project and updates
the statistics table in the README file between HTML comment markers.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, shell=True, capture_output=True, text=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=text)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1


def get_test_stats():
    """Get test statistics by running pytest."""
    print("📊 Gathering test statistics...")

    # Run the same comprehensive test suite as 'make test' but capture stats
    print("📊 Running comprehensive test suite (like 'make test')...")

    # Step 1: Container tests (unit + integration except UI validation)
    print("📊 Step 1: Container tests...")
    exclude_args = (
        "--ignore=tests/functional/test_overtime_ui_display.py --ignore=tests/integration/test_ui_validation.py"
    )
    container_cmd = f"docker compose exec -T web pytest tests/ --tb=no -q --disable-warnings {exclude_args}"
    container_stdout, container_stderr, container_returncode = run_command(container_cmd)

    # Step 2: UI validation tests locally
    print("📊 Step 2: UI validation tests...")
    ui_cmd = "pytest tests/integration/test_ui_validation.py --tb=no -q --disable-warnings"
    if os.path.exists("venv"):
        ui_cmd = f"source venv/bin/activate && {ui_cmd}"
    ui_stdout, ui_stderr, ui_returncode = run_command(ui_cmd)

    # Step 3: Get coverage data from container tests
    print("📊 Step 3: Coverage data...")
    # First ensure containers are running
    run_command("docker compose up -d >/dev/null 2>&1 && sleep 3", shell=True)

    # Run coverage on unit tests only to get reliable coverage data
    # Full test coverage can timeout or produce too much output
    coverage_cmd = (
        "docker compose exec -T web pytest --cov=app --cov-report=term tests/unit/ --tb=no -q --disable-warnings"
    )
    cov_stdout, cov_stderr, cov_returncode = run_command(coverage_cmd)

    # Parse test results and coverage
    test_results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    coverage_percent = "Unknown"
    coverage_lines = {"covered": 0, "total": 0}

    # Strip ANSI color codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # Parse container test results (main test suite)
    container_clean = ansi_escape.sub("", container_stdout + container_stderr)

    # Parse UI test results (if they ran successfully)
    ui_clean = ansi_escape.sub("", ui_stdout + ui_stderr)

    # Parse container tests first (this is the main test suite)
    container_summary = re.search(r"=+\s*(.*?)\s*in\s+[\d.]+s.*?=+", container_clean)
    if container_summary:
        summary_text = container_summary.group(1)
        count_patterns = [
            (r"(\d+)\s+passed", "passed"),
            (r"(\d+)\s+failed", "failed"),
            (r"(\d+)\s+skipped", "skipped"),
            (r"(\d+)\s+error", "errors"),  # Note: singular 'error' in some cases
        ]

        for pattern, status in count_patterns:
            match = re.search(pattern, summary_text)
            if match:
                test_results[status] = int(match.group(1))

    # Add UI test results (if they ran successfully and completed)
    ui_summary = re.search(r"=+\s*(.*?)\s*in\s+[\d.]+s.*?=+", ui_clean)
    if ui_summary and ui_returncode == 0:
        summary_text = ui_summary.group(1)
        count_patterns = [
            (r"(\d+)\s+passed", "passed"),
            (r"(\d+)\s+failed", "failed"),
            (r"(\d+)\s+skipped", "skipped"),
            (r"(\d+)\s+error", "errors"),
        ]

        for pattern, status in count_patterns:
            match = re.search(pattern, summary_text)
            if match:
                test_results[status] += int(match.group(1))

    test_results["total"] = sum(test_results.values())

    # Parse coverage percentage from output like "TOTAL ... 6%" or "TOTAL ... 66%"
    if cov_returncode != 0:
        print(f"⚠️  Coverage command failed with return code {cov_returncode}")
        if cov_stderr:
            print(f"⚠️  Coverage stderr: {cov_stderr[:200]}")
    elif cov_stdout and "TOTAL" in cov_stdout:
        clean_coverage_output = ansi_escape.sub("", cov_stdout)
        coverage_match = re.search(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%", clean_coverage_output)
        if coverage_match:
            total_lines = int(coverage_match.group(1))
            uncovered_lines = int(coverage_match.group(2))
            coverage_percent = coverage_match.group(3)
            coverage_lines = {"total": total_lines, "covered": total_lines - uncovered_lines}
            print(f"📊 Coverage found: {coverage_percent}% ({coverage_lines['covered']}/{total_lines} lines)")
        else:
            print("⚠️  Coverage TOTAL line not found in output")
            # Debug: show last few lines of output
            lines = clean_coverage_output.split("\n")
            print(f"⚠️  Last 5 lines of coverage output: {lines[-5:]}")
    else:
        print("⚠️  No coverage output received")

    return test_results, coverage_percent, coverage_lines


def get_file_stats():
    """Get file and line counts."""
    print("📁 Counting files and lines...")

    # Count test files
    test_files = {
        "unit": len(list(Path("tests/unit").rglob("*.py"))),
        "integration": len(list(Path("tests/integration").rglob("*.py"))),
        "functional": len(list(Path("tests/functional").rglob("*.py"))),
    }
    test_files["total"] = sum(test_files.values())

    # Count Python source files
    python_files = len(list(Path("app").rglob("*.py")))

    # Count total lines of code
    stdout, _, _ = run_command("find app/ -name '*.py' -exec wc -l {} + | tail -1")
    total_loc = 0
    if stdout:
        total_loc = int(stdout.split()[0])

    # Count dependencies from pyproject.toml
    deps_count = 0
    try:
        with open("pyproject.toml") as f:
            content = f.read()
            # Count lines with package dependencies (lines with quotes containing package names)
            deps_count = len(re.findall(r'^\s*"[^"]+>=', content, re.MULTILINE))
    except FileNotFoundError:
        pass

    return test_files, python_files, total_loc, deps_count


def get_project_info():
    """Get basic project information."""
    version = "0.2.0"  # Default
    try:
        with open("pyproject.toml") as f:
            content = f.read()
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if version_match:
                version = version_match.group(1)
    except FileNotFoundError:
        pass

    return {"version": version}


def format_test_status(test_results):
    """Format test results with emojis."""
    parts = []
    if test_results["passed"] > 0:
        parts.append(f"{test_results['passed']} ✅ passed")
    if test_results["failed"] > 0:
        parts.append(f"{test_results['failed']} ❌ failed")
    if test_results["skipped"] > 0:
        parts.append(f"{test_results['skipped']} ⏭️ skipped")
    if test_results["errors"] > 0:
        parts.append(f"{test_results['errors']} ⚠️ errors")

    return f"{test_results['total']} total ({', '.join(parts)})"


def generate_stats_table(
    test_results, coverage_percent, coverage_lines, test_files, python_files, total_loc, deps_count, project_info
):
    """Generate the statistics table markdown."""

    test_status = format_test_status(test_results)
    test_files_str = (
        f"{test_files['total']} files ({test_files['unit']} unit, "
        f"{test_files['integration']} integration, {test_files['functional']} functional)"
    )
    coverage_str = f"{coverage_percent}% ({coverage_lines['covered']:,} / {coverage_lines['total']:,} executable lines)"
    source_str = f"{python_files} Python files ({total_loc // 1000}k total LOC)"

    table = f"""## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Tests** | {test_status} |
| **Test Files** | {test_files_str} |
| **Code Coverage** | {coverage_str} |
| **Source Code** | {source_str} |
| **Dependencies** | {deps_count} total (core + dev/test) |
| **Python Version** | 3.11+ |
| **Code Quality** | Ruff linting + pytest |
| **License** | MIT |
| **Version** | {project_info["version"]} |
"""

    return table


def update_readme(new_stats_content):
    """Update the README.md file with new statistics."""
    readme_path = Path("README.md")

    if not readme_path.exists():
        print("❌ README.md not found!")
        return False

    # Read current README
    with open(readme_path) as f:
        content = f.read()

    # Find the statistics section between comment markers
    start_marker = "<!-- PROJECT_STATS_START -->"
    end_marker = "<!-- PROJECT_STATS_END -->"

    if start_marker not in content or end_marker not in content:
        print("❌ Statistics markers not found in README.md!")
        print("Please add the following markers around your statistics section:")
        print(f"  {start_marker}")
        print(f"  {end_marker}")
        return False

    # Replace content between markers
    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    replacement = f"{start_marker}\n{new_stats_content}\n{end_marker}"

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Write back to file
    with open(readme_path, "w") as f:
        f.write(new_content)

    print("✅ README.md updated successfully!")
    return True


def main():
    """Main function to update project statistics."""
    print("🔄 Updating project statistics...")

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    try:
        # Gather all statistics
        test_results, coverage_percent, coverage_lines = get_test_stats()
        test_files, python_files, total_loc, deps_count = get_file_stats()
        project_info = get_project_info()

        # Generate new statistics table
        new_stats = generate_stats_table(
            test_results,
            coverage_percent,
            coverage_lines,
            test_files,
            python_files,
            total_loc,
            deps_count,
            project_info,
        )

        # Update README
        if update_readme(new_stats):
            print("🎉 Project statistics updated successfully!")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error updating statistics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
