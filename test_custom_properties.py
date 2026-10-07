"""Unit tests for the INCLUDE_CUSTOM_PROPERTIES filtering helpers."""

import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from github import GithubException
from stale_repos import (
    get_custom_properties_map,
    get_inactive_repos,
    get_repo_custom_properties,
    matches_custom_properties,
    parse_custom_property_filters,
    repo_matches_custom_properties,
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
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
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


class GetCustomPropertiesMapTestCase(unittest.TestCase):
    """Test suite for the get_custom_properties_map function."""

    def test_builds_lowercased_map_from_org(self):
        """The map should be keyed by lowercased repo name."""
        mock_github = MagicMock()
        item1 = MagicMock(spec=["repository_name", "properties"])
        item1.repository_name = "Repo-One"
        item1.properties = {"owner": "my-team"}
        item2 = MagicMock(spec=["repository_name", "properties"])
        item2.repository_name = "repo-two"
        item2.properties = {"owner": "other-team"}
        mock_github.get_organization.return_value.list_custom_property_values.return_value = [
            item1,
            item2,
        ]

        result = get_custom_properties_map(mock_github, "example")

        self.assertEqual(
            result,
            {
                "repo-one": {"owner": "my-team"},
                "repo-two": {"owner": "other-team"},
            },
        )

    def test_raises_on_github_exception(self):
        """A GithubException (e.g. missing read:org) must abort the scan rather
        than look like an org with no matching values."""
        mock_github = MagicMock()
        mock_github.get_organization.return_value.list_custom_property_values.side_effect = GithubException(
            403, {"message": "Forbidden"}, None
        )

        with self.assertRaises(GithubException):
            get_custom_properties_map(mock_github, "example")

    def test_returns_none_without_organization(self):
        """Without an organization there is no bulk endpoint to call."""
        mock_github = MagicMock()

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = get_custom_properties_map(mock_github, None)
            output = mock_stdout.getvalue()

        self.assertIsNone(result)
        self.assertIn("INCLUDE_CUSTOM_PROPERTIES requires ORGANIZATION", output)


class GetRepoCustomPropertiesTestCase(unittest.TestCase):
    """Test suite for the get_repo_custom_properties function."""

    def test_flattens_property_list_into_dict(self):
        """The per-repo endpoint returns a list of {property_name, value}
        objects; these should be flattened into a plain dict."""
        mock_github = MagicMock()
        mock_github.requester.requestJsonAndCheck.return_value = (
            {},
            [{"property_name": "Lifecycle", "value": "maintenance"}],
        )
        repo = MagicMock(url="https://api.github.com/repos/example/repo")

        result = get_repo_custom_properties(mock_github, repo)

        self.assertEqual(result, {"Lifecycle": "maintenance"})
        mock_github.requester.requestJsonAndCheck.assert_called_once_with(
            "GET", "https://api.github.com/repos/example/repo/properties/values"
        )

    def test_raises_on_github_exception(self):
        """A GithubException must propagate so the scan aborts instead of
        treating the repo as having no properties."""
        mock_github = MagicMock()
        mock_github.requester.requestJsonAndCheck.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        repo = MagicMock(
            url="https://api.github.com/repos/example/repo",
            html_url="https://github.com/example/repo",
        )

        with self.assertRaises(GithubException):
            get_repo_custom_properties(mock_github, repo)


class RepoMatchesCustomPropertiesTestCase(unittest.TestCase):
    """Test suite for the repo_matches_custom_properties function."""

    def test_uses_values_map_when_present(self):
        """When a values_map is supplied, look the repo up by name in it
        rather than making a per-repo API call."""
        mock_github = MagicMock()
        repo = MagicMock(name="repo", spec=["name"])
        repo.name = "Repo-One"
        values_map = {"repo-one": {"owner": "my-team"}}

        result = repo_matches_custom_properties(
            mock_github, repo, [("owner", "my-team")], values_map
        )

        self.assertTrue(result)
        mock_github.requester.requestJsonAndCheck.assert_not_called()

    def test_repo_absent_from_values_map_does_not_match(self):
        """A repo missing from the bulk map (e.g. newly created) should not match."""
        mock_github = MagicMock()
        repo = MagicMock(name="repo", spec=["name"])
        repo.name = "unlisted-repo"
        values_map = {"repo-one": {"owner": "my-team"}}

        result = repo_matches_custom_properties(
            mock_github, repo, [("owner", "my-team")], values_map
        )

        self.assertFalse(result)

    def test_falls_back_to_per_repo_lookup_when_map_is_none(self):
        """A None values_map should route to the per-repo API call."""
        mock_github = MagicMock()
        mock_github.requester.requestJsonAndCheck.return_value = (
            {},
            [{"property_name": "owner", "value": "my-team"}],
        )
        repo = MagicMock(
            name="repo", spec=["name", "url"], url="https://api.github.com/repos/x/repo"
        )
        repo.name = "repo"

        result = repo_matches_custom_properties(
            mock_github, repo, [("owner", "my-team")], None
        )

        self.assertTrue(result)
        mock_github.requester.requestJsonAndCheck.assert_called_once()


class ResolveCustomPropertyFilterTestCase(unittest.TestCase):
    """Test suite for the resolve_custom_property_filter function."""

    def test_returns_none_when_env_var_unset(self):
        """Without INCLUDE_CUSTOM_PROPERTIES set, no API calls should be made."""
        mock_github = MagicMock()

        result = resolve_custom_property_filter(mock_github, "example")

        self.assertIsNone(result)
        mock_github.get_organization.assert_not_called()

    @patch.dict(os.environ, {"INCLUDE_CUSTOM_PROPERTIES": "owner=my-team"})
    def test_returns_filters_and_values_map_when_set(self):
        """With the env var set, it should parse the filters, print them, and
        fetch the values map for the given organization."""
        mock_github = MagicMock()
        mock_github.get_organization.return_value.list_custom_property_values.return_value = (
            []
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = resolve_custom_property_filter(mock_github, "example")
            output = mock_stdout.getvalue()

        self.assertEqual(result, ([("owner", "my-team")], {}))
        self.assertIn("Include custom properties: [('owner', 'my-team')]", output)


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
        matching_repo.get_topics.return_value = []

        non_matching_repo = MagicMock(
            html_url="https://github.com/example/non_matching_repo",
            pushed_at=forty_days_ago,
            archived=False,
            private=True,
        )
        non_matching_repo.name = "non_matching_repo"

        mock_github.get_organization.return_value = mock_org
        mock_org.get_repos.return_value = [matching_repo, non_matching_repo]
        mock_org.list_custom_property_values.return_value = [
            MagicMock(
                repository_name="matching_repo",
                properties={"owner": "my-team"},
            ),
            MagicMock(
                repository_name="non_matching_repo",
                properties={"owner": "other-team"},
            ),
        ]

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
