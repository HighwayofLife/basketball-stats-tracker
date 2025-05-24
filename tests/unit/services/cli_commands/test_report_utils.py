"""Unit tests for report utilities."""

from io import StringIO
from unittest.mock import MagicMock, patch

from app.services.cli_commands.report_utils import (
    print_nested_data,
    write_dict_to_csv,
    write_report_to_csv,
    write_value_to_csv,
)


class TestReportUtils:
    """Test report utility functions."""

    def test_print_nested_data_dict(self, capsys):
        """Test printing nested dictionary."""
        data = {"name": "Test Player", "stats": {"points": 20, "rebounds": 10}}

        print_nested_data(data)

        captured = capsys.readouterr()
        assert "Name: Test Player" in captured.out
        assert "Stats:" in captured.out
        assert "Points: 20" in captured.out
        assert "Rebounds: 10" in captured.out

    def test_print_nested_data_list_of_dicts(self, capsys):
        """Test printing list of dictionaries."""
        data = [{"name": "Player 1", "points": 20}, {"name": "Player 2", "points": 15}]

        with patch("app.services.cli_commands.report_utils.tabulate") as mock_tabulate:
            mock_tabulate.return_value = "Mocked table"
            print_nested_data(data)

            # Should use tabulate for list of similar dicts
            mock_tabulate.assert_called_once()

    def test_print_nested_data_percentage_formatting(self, capsys):
        """Test percentage formatting."""
        data = {"ft_pct": 0.875}

        print_nested_data(data)

        captured = capsys.readouterr()
        assert "Ft Pct: 0.875" in captured.out

    def test_write_dict_to_csv(self):
        """Test writing dictionary to CSV."""
        csv_file = StringIO()
        csv_writer = MagicMock()
        data = {"field1": "value1", "field2": "value2"}

        write_dict_to_csv(data, csv_writer)

        # Verify write was called for each field
        assert csv_writer.writerow.call_count == 2

    def test_write_value_to_csv_dict(self):
        """Test writing dict value to CSV."""
        csv_writer = MagicMock()
        value = {"nested": "value"}

        write_value_to_csv(value, csv_writer, "test_key")

        # Should recursively call write_dict_to_csv
        # which will write the nested value

    def test_write_value_to_csv_list(self):
        """Test writing list value to CSV."""
        csv_writer = MagicMock()
        value = ["item1", "item2"]

        write_value_to_csv(value, csv_writer, "test_key")

        # Should write each item
        assert csv_writer.writerow.call_count == 2

    def test_write_value_to_csv_scalar(self):
        """Test writing scalar value to CSV."""
        csv_writer = MagicMock()
        value = "test_value"

        write_value_to_csv(value, csv_writer, "test_key")

        csv_writer.writerow.assert_called_once_with(["Test Key", "test_value"])

    def test_write_report_to_csv_dict(self):
        """Test writing report dict to CSV."""
        csv_file = StringIO()
        data = {"field1": "value1", "field2": "value2"}

        with patch("csv.writer") as mock_csv_writer:
            writer_instance = MagicMock()
            mock_csv_writer.return_value = writer_instance

            write_report_to_csv(data, csv_file)

            # Should write header row
            writer_instance.writerow.assert_any_call(["Field", "Value"])

    def test_write_report_to_csv_list_of_dicts(self):
        """Test writing list of dicts to CSV."""
        csv_file = StringIO()
        data = [{"name": "Player 1", "points": 20}, {"name": "Player 2", "points": 15}]

        with patch("csv.DictWriter") as mock_dict_writer:
            writer_instance = MagicMock()
            mock_dict_writer.return_value = writer_instance

            write_report_to_csv(data, csv_file)

            # Should use DictWriter for list of similar dicts
            mock_dict_writer.assert_called_once()
            writer_instance.writeheader.assert_called_once()
            writer_instance.writerows.assert_called_once_with(data)
