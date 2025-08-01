# Codebase Optimization Notes

This document summarizes code quality issues discovered during review. Each item includes a brief description and suggested improvements to apply KISS, DRY, and SOLID principles.

## 1. Duplicated Listing Logic

`listing_commands.py` contains three nearly identical functions (`list_games`, `list_players`, `list_teams`). They each build tabular output and optionally write CSV files using repeated blocks of code.

**Suggested solution:** Extract the common CSV/table formatting into a reusable helper (e.g., `format_and_output_table(data, headers, output_file=None)`). This reduces duplication and simplifies adding new listing commands.

## 2. Stats Aggregation Complexity

`StatsEntryService.record_player_game_performance` loops over four quarters and updates totals manually. A later method, `add_player_quarter_stats`, repeats much of this logic.

**Suggested solution:** Create a dedicated utility or class for parsing shot strings and aggregating quarter statistics. This will keep the service concise and easier to maintain.

## 3. Report Generation Dispatch

`ReportCommands.generate_report` relies on a long `if/elif` chain to select report types and performs duplicate checks for team IDs.

**Suggested solution:** Map report type strings to handler functions in a dictionary (e.g., `report_handlers = {"game": self._game_report, ...}`). This follows the Open/Closed principle and allows adding new reports without editing a large conditional block.

## 4. Database Session Handling

Several CRUD modules manage the database session directly (`db.commit()`, `db.refresh()`), leading to repetitive code and inconsistent error handling.

**Suggested solution:** Implement repository methods or context managers that handle transactions. Centralizing this logic promotes cleaner code and easier debugging.

## 5. CSV/Console Formatting Duplication

Multiple CLI modules convert query results to CSV or formatted console tables using similar patterns with `csv.DictWriter` and `tabulate`.

**Suggested solution:** Introduce a `CsvConsoleFormatter` utility class that encapsulates these formatting routines. This adheres to DRY and makes future formatting changes easier.

## 6. Mixing CLI and Business Logic

Current CLI modules interleave user interaction (Typer `echo`) with database operations and business logic. This coupling complicates testing and future expansion.

**Suggested solution:** Route CLI arguments to service-layer functions that return data objects. The CLI layer should only handle argument parsing and user feedback, keeping business logic separate.

