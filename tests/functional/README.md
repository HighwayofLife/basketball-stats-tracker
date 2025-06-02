# Functional Tests

This directory contains functional (end-to-end) tests for the Basketball Stats Tracker web UI.

## Overview

Functional tests validate complete user workflows through the browser, ensuring the application works correctly from the user's perspective. These tests complement unit and integration tests by testing the full stack.

## Setup

To run functional tests, you need to install additional dependencies:

```bash
# Install Playwright and pytest plugin
pip install playwright pytest-playwright

# Install browser drivers
playwright install chromium firefox webkit
```

## Running Tests

1. Start the web server:
   ```bash
   make run  # Using Docker
   # OR
   basketball-stats web-server  # Using CLI
   ```

2. Run functional tests:
   ```bash
   # Run all functional tests
   pytest tests/functional/

   # Run with visible browser (headed mode)
   pytest tests/functional/ --headed

   # Run specific test file
   pytest tests/functional/test_csv_import_example.py

   # Generate HTML report
   pytest tests/functional/ --html=report.html
   ```

## Test Structure

- `test_csv_import_example.py` - Example test structure (not executable without Playwright)
- Future test files will cover:
  - `test_scorebook_entry.py` - Manual game entry tests
  - `test_game_reports.py` - Report viewing tests
  - `test_player_management.py` - Player CRUD tests
  - `test_team_management.py` - Team CRUD tests

## Writing New Tests

See the [UI Functional Testing Guide](../../docs/ui_functional_testing_guide.md) for detailed information on:
- Test structure and best practices
- Page Object Model pattern
- Debugging techniques
- CI/CD integration

## Note

The current `test_csv_import_example.py` is a demonstration of test structure and is not executable without Playwright installed. It shows how functional tests should be organized once the testing infrastructure is fully set up.
