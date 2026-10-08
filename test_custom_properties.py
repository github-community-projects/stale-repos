"""Unit tests for the INCLUDE_CUSTOM_PROPERTIES filtering helpers."""

import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from stale_repos import (
    get_inactive_repos,
    matches_custom_properties,
    parse_custom_property_filters,
    resolve_custom_property_filter,
)


class ParseCustomPropertyFiltersTestCase(unittest.TestCase):
    """Test suite for the parse_custom_property_filters function."""

    def test_parse_variations(self):
        """Cover the entry shapes the INCLUDE_CUSTOM_PROPERTIES value can take."""
        test_cases = [
            ("owner", [("owner", None)]),
            ("owner=my-team", [("owner", "my-team")]),
            (" owner = my-team ", [("owner", "my-team")]),
            ("a=b=c", [("a", "b=c")]),
            ("a,,b", [("a", None), ("b", None)]),
            ("OWNER=My-Team", [("owner", "my-team")]),
            (
                "owner=my-team,lifecycle=production",
                [("owner", "my-team"), ("lifecycle", "production")],
            ),
        ]

        for raw, expected in test_cases:
            with self.subTest(raw=raw):
                self.assertEqual(parse_custom_property_filters(raw), expected)

    def test_rejects_values_that_produce_no_valid_filter(self):
        """Values with no filters or an empty property name must not silently
        widen or empty the allow-list."""
        for raw in [",", " , ", "=my-team", "owner,=x"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_custom_property_filters(raw)


class MatchesCustomPropertiesTestCase(unittest.TestCase):
    """Test suite for the matches_custom_properties function."""

    def test_match_variations(self):
        """Cover the truth table for a single filter."""
        test_cases = [
            ({"owner": "my-team"}, [("owner", None)], True),
            ({}, [("owner", None)], False),
            ({"owner": ""}, [("owner", None)], False),
            ({"owner": None}, [("owner", None)], False),
            ({"owner": "my-team"}, [("owner", "my-team")], True),
            ({"owner": "other-team"}, [("owner", "my-team")], False),
            ({"team": ["platform", "sre"]}, [("team", "platform")], True),
            ({"team": ["platform", "sre"]}, [("team", "other")], False),
            ({"Owner": "My-Team"}, [("owner", "my-team")], True),
            ({"owner": "MY-TEAM"}, [("owner", "my-team")], True),
        ]

        for values, filters, expected in test_cases:
            with self.subTest(values=values, filters=filters):
                self.assertEqual(matches_custom_properties(values, filters), expected)

    def test_all_filters_must_match(self):
        """A repo with only one of two required properties should not match."""
        values = {"owner": "my-team"}
        filters = [("owner", "my-team"), ("lifecycle", "production")]

        self.assertFalse(matches_custom_properties(values, filters))


class ResolveCustomPropertyFilterTestCase(unittest.TestCase):
    """Test suite for the resolve_custom_property_filter function."""

    def test_returns_none_when_env_var_unset(self):
        """Without INCLUDE_CUSTOM_PROPERTIES set, no filtering happens."""
        self.assertIsNone(resolve_custom_property_filter("example"))

    @patch.dict(os.environ, {"INCLUDE_CUSTOM_PROPERTIES": "owner=my-team"})
    def test_returns_parsed_filters_and_prints_them(self):
        """The parsed filters are returned and echoed to the log."""
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = resolve_custom_property_filter("example")
            output = mock_stdout.getvalue()

        self.assertEqual(result, [("owner", "my-team")])
        self.assertIn("Include custom properties: [('owner', 'my-team')]", output)

    @patch.dict(os.environ, {"INCLUDE_CUSTOM_PROPERTIES": "owner=my-team"})
    def test_raises_without_organization(self):
        """Custom properties only exist for org-owned repos, so fail fast."""
        with self.assertRaisesRegex(ValueError, "requires ORGANIZATION"):
            resolve_custom_property_filter(None)


class GetInactiveReposWithIncludeCustomPropertiesTestCase(unittest.TestCase):
    """Verify get_inactive_repos honors the INCLUDE_CUSTOM_PROPERTIES environment variable."""

    def setUp(self):
        os.environ["INCLUDE_CUSTOM_PROPERTIES"] = "owner=my-team"

    def tearDown(self):
        del os.environ["INCLUDE_CUSTOM_PROPERTIES"]

    def test_only_matching_repos_are_considered(self):
        """Repos whose custom properties don't match should be skipped before
        any topic/exemption check, and never counted toward the report."""
        mock_github = MagicMock()
        mock_org = MagicMock()

        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        matching_repo = MagicMock(
            html_url="https://github.com/example/matching_repo",
            pushed_at=forty_days_ago,
            archived=False,
            private=True,
        )
        matching_repo.name = "matching_repo"
        matching_repo.custom_properties = {"owner": "my-team"}
        matching_repo.get_topics.return_value = []

        non_matching_repo = MagicMock(
            html_url="https://github.com/example/non_matching_repo",
            pushed_at=forty_days_ago,
            archived=False,
            private=True,
        )
        non_matching_repo.name = "non_matching_repo"
        non_matching_repo.custom_properties = {"owner": "other-team"}

        mock_github.get_organization.return_value = mock_org
        mock_org.get_repos.return_value = [matching_repo, non_matching_repo]

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            inactive_repos = get_inactive_repos(mock_github, 30, "example")
            output = mock_stdout.getvalue()

        self.assertIn("Include custom properties: [('owner', 'my-team')]", output)
        self.assertEqual(len(inactive_repos), 1)
        self.assertEqual(
            inactive_repos[0]["url"], "https://github.com/example/matching_repo"
        )
        # A filtered-out repo should never pay for a topics lookup.
        non_matching_repo.get_topics.assert_not_called()
