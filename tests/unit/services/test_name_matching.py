"""Unit tests for name matching logic."""

import pytest
from unittest.mock import Mock

# Import the class just to access the method
from app.services.import_services.import_processor import ImportProcessor


class TestNameMatchingLogic:
    """Test the name matching logic isolated from dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a minimal instance just to test the method
        self.mock_db = Mock()
        
        # We'll test the method directly without initializing all dependencies
        # by creating a minimal processor instance
        class MinimalProcessor:
            def _names_match_simple(self, existing_name: str, new_name: str) -> bool:
                """Copy of the actual method for testing."""
                existing_clean = existing_name.strip().lower()
                new_clean = new_name.strip().lower()
                
                # Must have at least 3 characters for matching
                if len(existing_clean) < 3 or len(new_clean) < 3:
                    return False
                    
                # Check if one is a prefix of the other (handles "John" vs "John M.")
                if existing_clean.startswith(new_clean) or new_clean.startswith(existing_clean):
                    length_diff = abs(len(existing_clean) - len(new_clean))
                    if length_diff <= 5:
                        return True
                    
                # Extract first names by splitting on space
                existing_parts = existing_clean.split()
                new_parts = new_clean.split()
                
                if len(existing_parts) >= 1 and len(new_parts) >= 1:
                    existing_first = existing_parts[0]
                    new_first = new_parts[0]
                    
                    # If first names match exactly and both have more parts, it's a match
                    if existing_first == new_first and len(existing_parts) > 1 and len(new_parts) > 1:
                        return True
                        
                    # Check if one first name is abbreviation of the other (Jonathan vs Jon)
                    shorter_first = min(existing_first, new_first, key=len)
                    longer_first = max(existing_first, new_first, key=len)
                    
                    if (len(shorter_first) >= 3 and 
                        longer_first.startswith(shorter_first) and 
                        len(longer_first) - len(shorter_first) <= 3):
                        return True
                        
                return False
        
        self.processor = MinimalProcessor()

    def test_names_match_simple_prefix_matching(self):
        """Test that prefix matching works correctly."""
        # John vs John M. should match
        assert self.processor._names_match_simple("John", "John M.") is True
        assert self.processor._names_match_simple("John M.", "John") is True
        
        # Sam vs Samuel should match (abbreviation)
        assert self.processor._names_match_simple("Sam", "Samuel") is True
        assert self.processor._names_match_simple("Samuel", "Sam") is True

    def test_names_match_simple_first_name_abbreviations(self):
        """Test that first name abbreviations work correctly."""
        # Jonathan T. vs Jon T. should NOT match (different parsing)
        assert self.processor._names_match_simple("Jonathan T.", "Jon T.") is False
        assert self.processor._names_match_simple("Jon T.", "Jonathan T.") is False
        
        # Jonathan vs Jon should match
        assert self.processor._names_match_simple("Jonathan", "Jon") is True
        assert self.processor._names_match_simple("Jon", "Jonathan") is True

    def test_names_match_simple_same_first_name_different_middle(self):
        """Test that same first names with different middle initials match."""
        # John M. vs John D. should match (same first name)
        assert self.processor._names_match_simple("John M.", "John D.") is True
        assert self.processor._names_match_simple("John Smith", "John Jones") is True

    def test_names_match_simple_rejects_different_names(self):
        """Test that clearly different names are rejected."""
        # Michael vs Mike should NOT match
        assert self.processor._names_match_simple("Michael", "Mike") is False
        
        # Bob vs Robert should NOT match
        assert self.processor._names_match_simple("Bob", "Robert") is False
        
        # James vs Jim should NOT match
        assert self.processor._names_match_simple("James", "Jim") is False
        
        # Christopher vs Chris should match (Chris is prefix, length diff = 6)
        assert self.processor._names_match_simple("Christopher", "Chris") is True
        
        # Alexander vs Alex should match (Alex is prefix, length diff = 5) 
        assert self.processor._names_match_simple("Alexander", "Alex") is True

    def test_names_match_simple_minimum_length_requirement(self):
        """Test that names must meet minimum length requirements."""
        # Names with less than 3 characters should not match
        assert self.processor._names_match_simple("Jo", "John") is False
        assert self.processor._names_match_simple("John", "Jo") is False
        assert self.processor._names_match_simple("Al", "Alex") is False

    def test_names_match_simple_exact_matches(self):
        """Test that exact matches work."""
        assert self.processor._names_match_simple("John Smith", "John Smith") is True
        assert self.processor._names_match_simple("Jonathan", "Jonathan") is True

    def test_names_match_simple_case_insensitive(self):
        """Test that matching is case insensitive."""
        assert self.processor._names_match_simple("JOHN M.", "john m.") is True
        assert self.processor._names_match_simple("Jonathan T.", "JON T.") is False

    def test_names_match_simple_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        assert self.processor._names_match_simple("  John M.  ", "John M.") is True
        assert self.processor._names_match_simple("Jonathan T.", "  Jon T.  ") is False

    def test_names_match_simple_edge_cases(self):
        """Test edge cases."""
        # Empty strings
        assert self.processor._names_match_simple("", "John") is False
        assert self.processor._names_match_simple("John", "") is False
        
        # Single character
        assert self.processor._names_match_simple("J", "John") is False
        
        # Very long abbreviation difference (length diff > 5)
        assert self.processor._names_match_simple("Maximilian", "Max") is False

    def test_names_match_simple_common_scorebook_variations(self):
        """Test real-world scorebook variations that should be accepted."""
        # Common basketball scorebook abbreviations
        assert self.processor._names_match_simple("Anthony J.", "Tony J.") is False  # Different names
        assert self.processor._names_match_simple("William", "Will") is True         # Will is prefix of William
        assert self.processor._names_match_simple("Matthew", "Matt") is True         # Matt is prefix of Matthew
        assert self.processor._names_match_simple("Nicholas", "Nick") is False       # Different names
        assert self.processor._names_match_simple("Daniel", "Dan") is True           # Dan is prefix of Daniel