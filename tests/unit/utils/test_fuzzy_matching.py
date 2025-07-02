"""Tests for fuzzy name matching utilities."""

from app.utils.fuzzy_matching import (
    extract_name_components,
    find_best_name_match,
    fuzzy_name_match,
    is_initial_match,
    levenshtein_distance,
    names_match_enhanced,
    normalize_name,
    similarity_ratio,
)


class TestFuzzyNameMatch:
    """Test fuzzy name matching functionality."""

    def test_exact_match(self):
        """Test exact name matching."""
        assert fuzzy_name_match("John Smith", "John Smith") is True
        assert fuzzy_name_match("john smith", "John Smith") is True
        assert fuzzy_name_match("JOHN SMITH", "john smith") is True

    def test_first_name_last_initial(self):
        """Test first name + last initial matching."""
        assert fuzzy_name_match("John Smith", "John S") is True
        assert fuzzy_name_match("John Smith", "John S.") is True
        assert fuzzy_name_match("John S", "John Smith") is True
        assert fuzzy_name_match("John S.", "John Smith") is True

        # Should not match different initials
        assert fuzzy_name_match("John Smith", "John B") is False

    def test_first_name_middle_initial(self):
        """Test first name + middle initial matching."""
        assert fuzzy_name_match("John Michael Smith", "John M Smith") is True
        assert fuzzy_name_match("John M Smith", "John Michael Smith") is True
        assert fuzzy_name_match("John M. Smith", "John Michael Smith") is True

        # First name match with one having middle name, other not
        assert fuzzy_name_match("John Smith", "John Michael Smith") is True
        assert fuzzy_name_match("John Michael Smith", "John Smith") is True

    def test_abbreviations(self):
        """Test common name abbreviations."""
        assert fuzzy_name_match("Jonathan", "Jon") is True
        assert fuzzy_name_match("Jon", "Jonathan") is True
        assert fuzzy_name_match("Michael", "Mike") is True
        assert fuzzy_name_match("Christopher", "Chris") is True
        assert fuzzy_name_match("Alexander", "Alex") is True
        assert fuzzy_name_match("Benjamin", "Ben") is True
        assert fuzzy_name_match("Zachary", "Zach") is True

    def test_nickname_matching(self):
        """Test common nickname variations."""
        assert fuzzy_name_match("William", "Bill") is True
        assert fuzzy_name_match("Bill", "William") is True
        assert fuzzy_name_match("Robert", "Bob") is True
        assert fuzzy_name_match("Richard", "Rick") is True
        assert fuzzy_name_match("James", "Jim") is True
        assert fuzzy_name_match("David", "Dave") is True
        assert fuzzy_name_match("Anthony", "Tony") is True

    def test_high_similarity_matching(self):
        """Test high similarity ratio matching."""
        assert fuzzy_name_match("John", "Jhon") is True  # Common typo
        assert fuzzy_name_match("Smith", "Smth") is False  # Too different
        assert fuzzy_name_match("Johnson", "Jonson") is True  # Minor difference

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty strings
        assert fuzzy_name_match("", "") is False
        assert fuzzy_name_match("John", "") is False
        assert fuzzy_name_match("", "John") is False

        # Very short names
        assert fuzzy_name_match("Jo", "John") is False
        assert fuzzy_name_match("J", "John") is False

        # Names that should not match
        assert fuzzy_name_match("John Smith", "Mike Johnson") is False
        assert fuzzy_name_match("John", "Michael") is False

    def test_real_world_cases(self):
        """Test real-world name variations from basketball rosters."""
        # Common CSV variations
        assert fuzzy_name_match("John Miller", "John M") is True
        assert fuzzy_name_match("Michael Jordan", "Mike Jordan") is True
        assert fuzzy_name_match("Christopher Paul", "Chris Paul") is True
        assert fuzzy_name_match("Anthony Davis", "Tony Davis") is True

        # Partial name entries
        assert fuzzy_name_match("Lebron James", "Lebron J") is True
        assert fuzzy_name_match("Stephen Curry", "Steph Curry") is True


class TestNormalizeName:
    """Test name normalization functionality."""

    def test_basic_normalization(self):
        """Test basic name normalization."""
        assert normalize_name("  John   Smith  ") == "john smith"
        assert normalize_name("JOHN SMITH") == "john smith"
        assert normalize_name("John.Smith") == "john smith"
        assert normalize_name("John,Smith") == "john smith"

    def test_whitespace_handling(self):
        """Test whitespace normalization."""
        assert normalize_name("John\t\tSmith") == "john smith"
        assert normalize_name("John\n\nSmith") == "john smith"
        assert normalize_name("John     Smith") == "john smith"


class TestExtractNameComponents:
    """Test name component extraction."""

    def test_single_name(self):
        """Test extraction from single names."""
        first, middle, last = extract_name_components("John")
        assert first == "john"
        assert middle is None
        assert last is None

    def test_two_names(self):
        """Test extraction from two names."""
        first, middle, last = extract_name_components("John Smith")
        assert first == "john"
        assert middle is None
        assert last == "smith"

    def test_three_names(self):
        """Test extraction from three names."""
        first, middle, last = extract_name_components("John Michael Smith")
        assert first == "john"
        assert middle == "michael"
        assert last == "smith"

    def test_name_with_initial(self):
        """Test extraction with middle initial."""
        first, middle, last = extract_name_components("John M. Smith")
        assert first == "john"
        assert middle == "m"
        assert last == "smith"


class TestIsInitialMatch:
    """Test initial matching functionality."""

    def test_basic_initial_matching(self):
        """Test basic initial matching."""
        assert is_initial_match("Michael", "M") is True
        assert is_initial_match("Michael", "m") is True
        assert is_initial_match("Michael", "M.") is True
        assert is_initial_match("Michael", "B") is False

    def test_edge_cases(self):
        """Test edge cases for initial matching."""
        assert is_initial_match("", "M") is False
        assert is_initial_match("Michael", "") is False
        assert is_initial_match("Michael", "Mi") is False  # Not an initial


class TestLevenshteinDistance:
    """Test Levenshtein distance calculation."""

    def test_basic_distance(self):
        """Test basic distance calculations."""
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("a", "") == 1
        assert levenshtein_distance("", "a") == 1
        assert levenshtein_distance("abc", "abc") == 0
        assert levenshtein_distance("abc", "ab") == 1
        assert levenshtein_distance("abc", "def") == 3

    def test_real_names(self):
        """Test distance with real name examples."""
        assert levenshtein_distance("John", "Jon") == 1
        assert levenshtein_distance("Michael", "Mike") == 4
        assert levenshtein_distance("Smith", "Smyth") == 1


class TestSimilarityRatio:
    """Test similarity ratio calculation."""

    def test_identical_strings(self):
        """Test identical strings."""
        assert similarity_ratio("John", "John") == 1.0
        assert similarity_ratio("john", "JOHN") == 1.0

    def test_different_strings(self):
        """Test different strings."""
        ratio = similarity_ratio("John", "Jane")
        assert 0.0 <= ratio <= 1.0
        assert ratio < 0.8  # Should be fairly low

    def test_similar_strings(self):
        """Test similar strings."""
        ratio = similarity_ratio("John", "Jon")
        assert ratio > 0.8  # Should be high


class TestFindBestNameMatch:
    """Test finding best name match from candidates."""

    def test_exact_match_found(self):
        """Test when exact match is found."""
        candidates = ["John Smith", "Mike Johnson", "Chris Paul"]
        result = find_best_name_match("John Smith", candidates)
        assert result is not None
        match, score = result
        assert match == "John Smith"
        assert score == 1.0

    def test_fuzzy_match_found(self):
        """Test when fuzzy match is found."""
        candidates = ["John Smith", "Mike Johnson", "Chris Paul"]
        result = find_best_name_match("John S", candidates)
        assert result is not None
        match, score = result
        assert match == "John Smith"
        assert score > 0.0

    def test_no_match_found(self):
        """Test when no good match is found."""
        candidates = ["John Smith", "Mike Johnson", "Chris Paul"]
        result = find_best_name_match("Totally Different", candidates)
        assert result is None

    def test_best_of_multiple_matches(self):
        """Test finding best match when multiple candidates match."""
        candidates = ["John Smith", "John S", "John Samuel"]
        result = find_best_name_match("John", candidates)
        assert result is not None
        match, score = result
        # Should pick one of the matches (exact logic may vary)
        assert match in candidates


class TestNamesMatchEnhanced:
    """Test backward compatibility function."""

    def test_backward_compatibility(self):
        """Test that enhanced function works like the original for basic cases."""
        # These should match (basic cases that original function handled)
        assert names_match_enhanced("John Smith", "John S") is True
        assert names_match_enhanced("Jonathan", "Jon") is True
        assert names_match_enhanced("John", "John M.") is True

        # These should not match
        assert names_match_enhanced("John Smith", "Mike Johnson") is False
        assert names_match_enhanced("John", "Michael") is False

    def test_enhanced_functionality(self):
        """Test enhanced functionality beyond original."""
        # These are new capabilities
        assert names_match_enhanced("William", "Bill") is True
        assert names_match_enhanced("Robert", "Bob") is True
        assert names_match_enhanced("John", "Jhon") is True  # Typo handling


class TestRealWorldScenarios:
    """Test real-world CSV import scenarios."""

    def test_common_csv_variations(self):
        """Test common variations found in CSV imports."""
        test_cases = [
            ("John Miller", "John M"),  # Last name to initial
            ("Michael Jordan", "M Jordan"),  # First name to initial
            ("Christopher Paul", "Chris Paul"),  # Common abbreviation
            ("Lebron James", "LeBron James"),  # Capitalization difference
            ("Stephen Curry", "Steph Curry"),  # Common shortened form
            ("Benjamin Wallace", "Ben Wallace"),  # Standard abbreviation
            ("Alexander Hamilton", "Alex Hamilton"),  # Standard abbreviation
            ("Jonathan Taylor", "Jon Taylor"),  # Standard abbreviation
            ("Zachary Smith", "Zach Smith"),  # Standard abbreviation
            ("Michael Jordan", "Mike Jordan"),  # Common nickname
        ]

        for existing_name, csv_name in test_cases:
            assert fuzzy_name_match(existing_name, csv_name) is True, f"Failed: {existing_name} vs {csv_name}"

    def test_should_not_match_cases(self):
        """Test cases that should definitely not match."""
        test_cases = [
            ("John Smith", "Mike Johnson"),  # Completely different
            ("John", "Michael"),  # Different first names
            ("Smith", "Johnson"),  # Different last names only
            ("John A Smith", "John B Smith"),  # Different middle initials
            ("John", "J"),  # Too short
            ("A", "B"),  # Single letters
        ]

        for name1, name2 in test_cases:
            assert fuzzy_name_match(name1, name2) is False, f"Should not match: {name1} vs {name2}"
