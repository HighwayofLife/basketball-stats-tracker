"""
Fuzzy name matching utilities for player identification.

This module provides enhanced name matching capabilities for CSV imports,
allowing for common variations, abbreviations, and minor typos in player names.
"""

import re
from difflib import SequenceMatcher


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        The minimum number of single-character edits needed to transform s1 into s2
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings using SequenceMatcher.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison by removing extra whitespace and standardizing format.

    Args:
        name: Raw name string

    Returns:
        Normalized name string
    """
    # Remove common punctuation and replace with spaces
    normalized = re.sub(r"[.,]", " ", name.strip().lower())

    # Remove extra whitespace and convert to lowercase
    normalized = re.sub(r"\s+", " ", normalized.strip())

    return normalized


def extract_name_components(name: str) -> tuple[str, str | None, str | None]:
    """
    Extract first name, last name, and middle initial/name from a full name.

    Args:
        name: Full name string

    Returns:
        Tuple of (first_name, middle_name_or_initial, last_name)
    """
    normalized = normalize_name(name)
    parts = normalized.split()

    if len(parts) == 1:
        return parts[0], None, None
    elif len(parts) == 2:
        # Could be "John Smith" or "John M" (first + middle initial)
        # If second part is single letter (with or without period), treat as middle initial
        if len(parts[1].rstrip(".")) == 1:
            # "John M" -> first="John", middle="M", last=None
            return parts[0], parts[1].rstrip("."), None
        else:
            # "John Smith" -> first="John", middle=None, last="Smith"
            return parts[0], None, parts[1]
    elif len(parts) >= 3:
        # Handle cases like "John Michael Smith" or "John M Smith"
        return parts[0], parts[1], parts[-1]

    return name.lower(), None, None


def is_initial_match(full_name: str, initial: str) -> bool:
    """
    Check if an initial matches the first letter of a full name.

    Args:
        full_name: Full name (e.g., "Michael")
        initial: Single letter or letter with period (e.g., "M" or "M.")

    Returns:
        True if the initial matches the first letter of the full name
    """
    if not full_name or not initial:
        return False

    # Remove period from initial if present
    clean_initial = initial.strip().rstrip(".").lower()

    return len(clean_initial) == 1 and full_name.lower().startswith(clean_initial)


def fuzzy_name_match(existing_name: str, new_name: str, threshold: float = 0.8) -> bool:
    """
    Enhanced fuzzy matching for player names with multiple strategies.

    This function implements several matching strategies in order of confidence:
    1. Exact match (case-insensitive)
    2. First name + last initial matching (e.g., "John Smith" vs "John S")
    3. First name + middle initial matching (e.g., "John Michael Smith" vs "John M Smith")
    4. Abbreviation matching (e.g., "Jonathan" vs "Jon")
    5. High similarity ratio with Levenshtein distance check

    Args:
        existing_name: Name currently in database
        new_name: Name from CSV import
        threshold: Minimum similarity ratio for fuzzy matching (0.0-1.0)

    Returns:
        True if names are similar enough to be considered the same player
    """
    if not existing_name or not new_name:
        return False

    existing_norm = normalize_name(existing_name)
    new_norm = normalize_name(new_name)

    # Strategy 1: Exact match
    if existing_norm == new_norm:
        return True

    # Strategy 2: High similarity with short distance (only for very similar names)
    ratio = similarity_ratio(existing_norm, new_norm)
    if ratio >= 0.95:  # Very high similarity only
        return True

    # Extract name components
    existing_first, existing_middle, existing_last = extract_name_components(existing_name)
    new_first, new_middle, new_last = extract_name_components(new_name)

    # Require that first names are related somehow for any match
    first_names_related = False

    if existing_first and new_first:
        # Check for exact first name match
        if existing_first == new_first:
            first_names_related = True
        else:
            # Check for initial matching (e.g., "Michael" vs "M")
            # Allow this for now, will filter single-letter-only names later
            if is_initial_match(existing_first, new_first) or is_initial_match(new_first, existing_first):
                first_names_related = True

            # Check for abbreviations
            shorter = min(existing_first, new_first, key=len)
            longer = max(existing_first, new_first, key=len)

            if (
                len(shorter) >= 3 and longer.startswith(shorter) and len(longer) - len(shorter) <= 4
            ):  # Allow reasonable abbreviations
                first_names_related = True

            # Check for common nicknames
            common_nicknames = {
                "william": ["bill", "will", "billy"],
                "robert": ["bob", "rob", "bobby"],
                "richard": ["rick", "dick", "richie"],
                "michael": ["mike", "mick"],
                "james": ["jim", "jimmy"],
                "david": ["dave", "davy"],
                "christopher": ["chris"],
                "matthew": ["matt"],
                "daniel": ["dan", "danny"],
                "thomas": ["tom", "tommy"],
                "anthony": ["tony"],
                "joshua": ["josh"],
                "andrew": ["andy", "drew"],
                "joseph": ["joe", "joey"],
                "jonathan": ["jon"],
                "benjamin": ["ben", "benny"],
                "nicholas": ["nick"],
                "alexander": ["alex"],
                "zachary": ["zach"],
                "stephen": ["steve", "steph"],
            }

            # Check if one is a common nickname of the other
            for full_name, nicknames in common_nicknames.items():
                if (
                    (existing_first == full_name and new_first in nicknames)
                    or (new_first == full_name and existing_first in nicknames)
                    or (existing_first in nicknames and new_first == full_name)
                    or (new_first in nicknames and existing_first == full_name)
                ):
                    first_names_related = True
                    break

    # Only proceed with matching if first names are related OR we have very high similarity for single names
    if not first_names_related:
        # For single letter names, be much more strict
        if len(existing_norm) == 1 or len(new_norm) == 1:
            return False

        # Allow very high similarity matches for single names (like last names) with strict distance check
        if ratio >= 0.9 and (not existing_last or not new_last):
            # Additional check: ensure the difference is just 1-2 characters for single names
            distance = levenshtein_distance(existing_norm, new_norm)
            if distance <= 2:
                return True
        return False

    # Strategy 3: First name + last initial matching - but only if last initials match
    if existing_first and new_first and existing_last and new_last:
        # Check for exact first name + last initial match
        if existing_first == new_first and (
            is_initial_match(existing_last, new_last) or is_initial_match(new_last, existing_last)
        ):
            return True

        # Also check first initial + last name (e.g., "Michael Jordan" vs "M Jordan")
        if existing_last == new_last and (
            is_initial_match(existing_first, new_first) or is_initial_match(new_first, existing_first)
        ):
            return True

    # Strategy 4: First name + middle initial matching
    if (
        existing_first
        and new_first
        and first_names_related
        and existing_last
        and new_last
        and existing_last == new_last
    ):
        # Only check middle names if both first and last names have some similarity
        if existing_middle and new_middle:
            # Both have middle names/initials - they must match or be initials of each other
            return (
                is_initial_match(existing_middle, new_middle)
                or is_initial_match(new_middle, existing_middle)
                or existing_middle == new_middle
            )
        elif (existing_middle and not new_middle) or (new_middle and not existing_middle):
            # One has middle name, other doesn't - still a potential match if first names are related
            return True
        else:
            # Neither has middle names, just first + last match with related first names
            return True

    # Strategy 5: Handle cases where one name has last and other has middle initial
    # e.g. "John Smith" vs "John B" - need to check if last name matches middle initial
    if first_names_related and (not existing_last or not new_last):
        # If one has a last name and the other has a middle initial, check if they match
        if existing_last and new_middle and not new_last:
            # e.g., "John Smith" vs "John B" -> check if "Smith" starts with "B"
            return is_initial_match(existing_last, new_middle)
        elif new_last and existing_middle and not existing_last:
            # e.g., "John B" vs "John Smith" -> check if "Smith" starts with "B"
            return is_initial_match(new_last, existing_middle)
        elif not existing_last and not new_last:
            # Both are single names - but don't allow single letter matches like "J" vs "John"
            return not (len(existing_norm) == 1 or len(new_norm) == 1)
        else:
            # One has last name, other doesn't - allow if not single letter
            return not (len(existing_norm) == 1 or len(new_norm) == 1)

    # Strategy 6: Medium similarity with distance check (only if first names are related)
    if first_names_related and ratio >= 0.8:
        # Additional check: Levenshtein distance should be reasonable
        max_distance = max(2, min(len(existing_norm), len(new_norm)) // 4)
        if levenshtein_distance(existing_norm, new_norm) <= max_distance:
            return True

    return False


def find_best_name_match(
    target_name: str, candidate_names: list[str], threshold: float = 0.8
) -> tuple[str, float] | None:
    """
    Find the best matching name from a list of candidates.

    Args:
        target_name: Name to match against
        candidate_names: List of candidate names to check
        threshold: Minimum similarity threshold

    Returns:
        Tuple of (best_match_name, similarity_score) or None if no good match found
    """
    best_match = None
    best_score = 0.0

    for candidate in candidate_names:
        if fuzzy_name_match(target_name, candidate, threshold):
            score = similarity_ratio(target_name, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

    return (best_match, best_score) if best_match else None


# Backward compatibility: keep the same interface as the existing function
def names_match_enhanced(existing_name: str, new_name: str) -> bool:
    """
    Enhanced version of the original _names_match_simple function.

    Provides backward compatibility while adding fuzzy matching capabilities.

    Args:
        existing_name: Name currently in database
        new_name: Name from CSV import

    Returns:
        True if names are similar enough to accept
    """
    return fuzzy_name_match(existing_name, new_name, threshold=0.75)
