"""Utility functions for report formatting and output."""

import csv
from typing import Any

import typer
from tabulate import tabulate  # type: ignore


def display_report_console(report_data: Any) -> None:
    """
    Display a report in the console.

    Args:
        report_data: Dictionary containing the report data
    """
    # Recursively print nested dictionaries and lists
    print_nested_data(report_data)


def print_nested_data(data: Any, indent: int = 0) -> None:
    """
    Recursively print nested dictionaries and lists with proper indentation.

    Args:
        data: Data to print (dictionary, list, or scalar value)
        indent: Current indentation level
    """
    indent_str = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict | list):
                typer.echo(f"{indent_str}{key.replace('_', ' ').title()}:")
                print_nested_data(value, indent + 1)
            else:
                # Format special values
                if key.endswith("_pct") and value is not None:
                    value = f"{value:.3f}"
                typer.echo(f"{indent_str}{key.replace('_', ' ').title()}: {value}")
    elif isinstance(data, list):
        # Special handling for lists of dictionaries - use tabulate if they have the same keys
        if data and all(isinstance(item, dict) for item in data) and len({tuple(item.keys()) for item in data}) == 1:
            typer.echo(tabulate(data, headers="keys", tablefmt="grid"))
            return

        # Otherwise, just print each item with indentation
        for i, item in enumerate(data):
            if isinstance(item, dict | list):
                typer.echo(f"{indent_str}Item {i + 1}:")
                print_nested_data(item, indent + 1)
            else:
                typer.echo(f"{indent_str}- {item}")
    else:
        typer.echo(f"{indent_str}{data}")


def write_report_to_csv(report_data: Any, csvfile: Any) -> None:
    """
    Write a report to a CSV file.

    Args:
        report_data: Dictionary containing the report data
        csvfile: File object to write to
    """
    # Handle different report structures
    writer = csv.writer(csvfile)

    if isinstance(report_data, dict):
        # Write a header row with "Field" and "Value"
        writer.writerow(["Field", "Value"])
        write_dict_to_csv(report_data, writer)
    elif isinstance(report_data, list):
        # If it's a list of dictionaries with the same keys, write as a table
        if (
            report_data
            and all(isinstance(item, dict) for item in report_data)
            and len({tuple(item.keys()) for item in report_data}) == 1
        ):
            dict_writer = csv.DictWriter(csvfile, fieldnames=report_data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(report_data)
            return

        # Otherwise, just write each item
        for item in report_data:
            write_value_to_csv(item, writer)


def write_dict_to_csv(data: dict[str, Any], writer: Any, prefix: str = "") -> None:
    """
    Recursively write a dictionary to a CSV writer.

    Args:
        data: Dictionary to write
        writer: CSV writer object
        prefix: Prefix for nested keys
    """
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        write_value_to_csv(value, writer, full_key)


def write_value_to_csv(value: Any, writer: Any, key: str | None = None) -> None:
    """
    Write a value to a CSV writer.

    Args:
        value: Value to write
        writer: CSV writer object
        key: Key for the value (if any)
    """
    key_str = "" if key is None else key

    if isinstance(value, dict):
        write_dict_to_csv(value, writer, key_str)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            item_key = f"{key_str}[{i}]" if key_str else f"Item {i + 1}"
            write_value_to_csv(item, writer, item_key)
    else:
        if key_str:
            writer.writerow([key_str.replace("_", " ").title(), value])
