"""
Unit tests for the auth_to_github() function.

This module contains a set of unit tests to verify the behavior of the auth_to_github() function.
The function is responsible for connecting to GitHub.com or GitHub Enterprise,
depending on environment variables.

The tests cover different scenarios, such as successful authentication with both enterprise URL
and token, authentication with only a token, missing environment variables, and authentication
failures.

To run the tests, execute this module as the main script.

Example:
    $ pytest test_auth_to_github.py

"""

import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import github3.github
from stale_repos import (
    get_active_date,
    get_days_since_last_pr,
    get_days_since_last_release,
    get_inactive_repos,
    is_repo_exempt,
    output_to_json,
    set_repo_data,
)


class GetInactiveReposTestCase(unittest.TestCase):
    """
    Unit test case for the get_inactive_repos() function.

    This test case class verifies the behavior and correctness of the get_inactive_repos()
    function, which gets the URL and days inactive for repositories that exceed the
    specified threshold.

    ...

    Test methods:
        - test_print_inactive_repos_with_inactive_repos: Tests printing of inactive repos
          that exceed the threshold.
        - test_print_inactive_repos_with_no_inactive_repos: Tests printing of no inactive repos.

    """

    def setUp(self):
        """Set up the environment variables for the test case."""
        os.environ["EXEMPT_TOPICS"] = "topic1,topic2"

    def tearDown(self):
        """Tear down the environment variables for the test case."""
        del os.environ["EXEMPT_TOPICS"]

    def test_get_inactive_repos_with_inactive_repos(self):
        """Test that get_inactive_repos returns the expected list of inactive repos.

        This test uses a MagicMock object to simulate a GitHub API connection with a list
        of repositories with varying levels of inactivity. It then calls the get_inactive_repos
        function with the mock GitHub API connection and a threshold of 30 days. Finally, it
        checks that the function returns the expected list of inactive repos.

        """
        # Create a MagicMock object to simulate a GitHub API connection
        mock_github = MagicMock()

        # Create a MagicMock object to simulate the organization object returned by the
        # GitHub API connection
        mock_org = MagicMock()

        # Create MagicMock objects to simulate the repositories returned by the organization object
        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        twenty_days_ago = datetime.now(timezone.utc) - timedelta(days=20)
        mock_repo1 = MagicMock(
            html_url="https://github.com/example/repo1",
            pushed_at=twenty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        mock_repo1.topics().names = []
        mock_repo2 = MagicMock(
            html_url="https://github.com/example/repo2",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        mock_repo2.topics().names = []
        mock_repo3 = MagicMock(
            html_url="https://github.com/example/repo3",
            pushed_at=forty_days_ago.isoformat(),
            archived=True,
            private=True,
        )
        mock_repo3.topics().names = []

        # Set up the MagicMock objects to return the expected values when called
        mock_github.organization.return_value = mock_org
        mock_org.repositories.return_value = [
            mock_repo1,
            mock_repo2,
            mock_repo3,
        ]

        # Call the get_inactive_repos function with the mock GitHub API
        # connection and a threshold of 30 days
        inactive_repos = get_inactive_repos(mock_github, 30, "example")

        # Check that the function returns the expected list of inactive repos
        expected_inactive_repos = [
            {
                "url": "https://github.com/example/repo2",
                "days_inactive": 40,
                "last_push_date": forty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": None,
                "days_since_last_pr": None,
            }
        ]
        assert inactive_repos == expected_inactive_repos

    def test_get_inactive_repos_with_no_inactive_repos(self):
        """Test getting with no inactive repos.

        This test verifies that the get_inactive_repos() function
        does not show anything when there are no repositories that
        exceed the specified threshold.

        """
        mock_github = MagicMock()
        mock_org = MagicMock()

        # Create a mock repository objects
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        mock_repo1 = MagicMock(
            pushed_at=thirty_days_ago.isoformat(),
            html_url="https://github.com/example/repo",
            archived=False,
        )
        mock_repo2 = MagicMock(
            pushed_at=None,
            html_url="https://github.com/example/repo2",
            archived=False,
        )

        mock_github.organization.return_value = mock_org
        mock_org.repositories.return_value = [
            mock_repo1,
            mock_repo2,
        ]

        # Call the function with a threshold of 40 days
        inactive_days_threshold = 40
        organization = "example"
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            get_inactive_repos(mock_github, inactive_days_threshold, organization)
            output = mock_stdout.getvalue()

        # Check that the output contains the expected repo URL and days inactive
        expected_output = (
            f"Exempt topics: ['topic1', 'topic2']\n"
            f"Found 0 stale repos in {organization}\n"
        )
        self.assertEqual(expected_output, output)

    def test_get_inactive_repos_with_exempt_topics(self):
        """Test that the get_inactive_repos function does not return exempt repos."""

        mock_github = MagicMock()
        mock_org = MagicMock()

        # create a mock repository with exempt topics
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        mock_repo1 = MagicMock(
            pushed_at=thirty_days_ago.isoformat(),
            html_url="https://github.com/example/repo",
            archived=False,
        )
        mock_repo1.topics().names = ["topic1", "topic2"]

        mock_repo2 = MagicMock(
            pushed_at=thirty_days_ago.isoformat(),
            html_url="https://github.com/example/repo2",
            archived=False,
        )
        mock_repo2.topics().names = ["topic3", "topic4"]

        mock_github.organization.return_value = mock_org
        mock_org.repositories.return_value = [
            mock_repo1,
            mock_repo2,
        ]

        # Call the function with a threshold of 20 days
        inactive_days_threshold = 20
        organization = "example"
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            get_inactive_repos(mock_github, inactive_days_threshold, organization)
            output = mock_stdout.getvalue()

        # Check that the output contains the expected repo URL and days inactive
        expected_output = (
            f"Exempt topics: ['topic1', 'topic2']\n"
            f"https://github.com/example/repo is exempt from stale repo check\n"
            f"https://github.com/example/repo2 30 days inactive\n"
            f"Found 1 stale repos in {organization}\n"
        )
        self.assertEqual(expected_output, output)

    def test_get_inactive_repos_with_no_organization_set(self):
        """Test that get_inactive_repos returns the expected list of inactive repos
        when no organization is set.

        This test uses a MagicMock object to simulate a GitHub API connection with a list
        of repositories with varying levels of inactivity. It then calls the get_inactive_repos
        function with the mock GitHub API connection and a threshold of 30 days where
        organization is set to None. Finally, it checks that the function returns the
        expected list of inactive repos.

        """
        # Create a MagicMock object to simulate a GitHub API connection
        mock_github = MagicMock()

        # Create MagicMock objects to simulate the repositories returned by the organization object
        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        twenty_days_ago = datetime.now(timezone.utc) - timedelta(days=20)
        mock_repo1 = MagicMock(
            html_url="https://github.com/example/repo1",
            pushed_at=twenty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        mock_repo1.topics().names = []
        mock_repo2 = MagicMock(
            html_url="https://github.com/example/repo2",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        mock_repo2.topics().names = []
        mock_repo3 = MagicMock(
            html_url="https://github.com/example/repo3",
            pushed_at=forty_days_ago.isoformat(),
            archived=True,
            private=True,
        )
        mock_repo3.topics().names = []

        # Set up the MagicMock objects to return the expected values when called
        mock_github.repositories.return_value = [
            mock_repo1,
            mock_repo2,
            mock_repo3,
        ]

        # Call the get_inactive_repos function with the mock GitHub API
        # connection and a threshold of 30 days
        inactive_repos = get_inactive_repos(mock_github, 30, None)

        # Check that the function returns the expected list of inactive repos
        expected_inactive_repos = [
            {
                "url": "https://github.com/example/repo2",
                "days_inactive": 40,
                "last_push_date": forty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": None,
                "days_since_last_pr": None,
            }
        ]
        assert inactive_repos == expected_inactive_repos

    @patch.dict(os.environ, {"ACTIVITY_METHOD": "default_branch_updated"})
    def test_get_inactive_repos_with_default_branch_updated(self):
        """Test that get_inactive_repos works with alternative method.

        This test uses a MagicMock object to simulate a GitHub API connection with a list
        of repositories with varying levels of inactivity. It then calls the get_inactive_repos
        function with the mock GitHub API connection, a threshold of 30 days, and the
        default_branch_updated setting.  It mocks the branch method on the repo object to return
        the necessary data for the active_date determination Finally, it checks that the function
        returns the expected list of inactive repos.

        """
        # Create a MagicMock object to simulate a GitHub API connection
        mock_github = MagicMock()

        # Create a MagicMock object to simulate the organization object returned by the
        # GitHub API connection
        mock_org = MagicMock()

        # Create MagicMock objects to simulate the repositories returned by the organization object
        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        twenty_days_ago = datetime.now(timezone.utc) - timedelta(days=20)
        mock_repo1 = MagicMock(
            html_url="https://github.com/example/repo1",
            default_branch="master",
            archived=False,
            private=True,
        )
        mock_repo1.topics().names = []
        mock_repo1.branch().commit.commit.as_dict = MagicMock(
            return_value={"committer": {"date": twenty_days_ago.isoformat()}}
        )
        mock_repo2 = MagicMock(
            html_url="https://github.com/example/repo2",
            archived=False,
            private=True,
        )
        mock_repo2.topics().names = []
        mock_repo2.branch().commit.commit.as_dict = MagicMock(
            return_value={"committer": {"date": forty_days_ago.isoformat()}}
        )
        mock_repo3 = MagicMock(
            html_url="https://github.com/example/repo3",
            archived=True,
            private=True,
        )
        mock_repo3.topics().names = []
        mock_repo3.branch().commit.commit.as_dict = MagicMock(
            return_value={"committer": {"date": forty_days_ago.isoformat()}}
        )

        # Set up the MagicMock objects to return the expected values when called
        mock_github.organization.return_value = mock_org
        mock_org.repositories.return_value = [
            mock_repo1,
            mock_repo2,
            mock_repo3,
        ]

        # Call the get_inactive_repos function with the mock GitHub API
        # connection and a threshold of 30 days
        inactive_repos = get_inactive_repos(mock_github, 30, "example")

        # Check that the function returns the expected list of inactive repos
        expected_inactive_repos = [
            {
                "url": "https://github.com/example/repo2",
                "days_inactive": 40,
                "last_push_date": forty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": None,
                "days_since_last_pr": None,
            }
        ]
        assert inactive_repos == expected_inactive_repos


@patch.dict(os.environ, {"ACTIVITY_METHOD": "default_branch_updated"})
class GetActiveDateTestCase(unittest.TestCase):
    """
    Unit test case for the get_active_date() function.

    This test case class verifies that get_active_date will return None if
    github3 throws any kind of exception.
    """

    def test_returns_none_for_exception(self):
        """Test that get will return None if github3 throws any kind of exception."""
        repo = MagicMock(
            name="repo", default_branch="main", spec=["branch", "html_url"]
        )

        repo.branch.side_effect = github3.exceptions.NotFoundError(
            resp=MagicMock(status_code=404)
        )
        result = get_active_date(repo)

        assert result is None


class OutputToJson(unittest.TestCase):
    """
    Unit test case for the output_to_json() function.
    """

    def test_output_to_json(self):
        """Test that output_to_json returns the expected json string.

        This test creates a list of inactive repos and calls the
        output_to_json function with the list. It then checks that the
        function returns the expected json string.

        """
        thirty_one_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        twenty_nine_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        # Create a list of inactive repos
        inactive_repos = [
            {
                "url": "https://github.com/example/repo1",
                "days_inactive": 31,
                "last_push_date": thirty_one_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": 3,
                "days_since_last_pr": 2,
            },
            {
                "url": "https://github.com/example/repo2",
                "days_inactive": 30,
                "last_push_date": thirty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": 1,
                "days_since_last_pr": None,
            },
            {
                "url": "https://github.com/example/repo3",
                "days_inactive": 29,
                "last_push_date": twenty_nine_days_ago.date().isoformat(),
                "visibility": "public",
                "days_since_last_release": None,
                "days_since_last_pr": 5,
            },
        ]

        # Call the output_to_json function with the list of inactive repos
        expected_json = json.dumps(
            [
                {
                    "url": "https://github.com/example/repo1",
                    "daysInactive": 31,
                    "lastPushDate": thirty_one_days_ago.date().isoformat(),
                    "visibility": "private",
                },
                {
                    "url": "https://github.com/example/repo2",
                    "daysInactive": 30,
                    "lastPushDate": thirty_days_ago.date().isoformat(),
                    "visibility": "private",
                },
                {
                    "url": "https://github.com/example/repo3",
                    "daysInactive": 29,
                    "lastPushDate": twenty_nine_days_ago.date().isoformat(),
                    "visibility": "public",
                },
            ]
        )
        actual_json = output_to_json(inactive_repos)
        assert actual_json == expected_json

    def test_json_file(self):
        """Test that output_to_json writes JSON data to a file

        This test checks that output_to_json correctly writes its JSON data
        to a file named "stale_repos.json"
        """
        thirty_one_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        twenty_nine_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        # Create a list of inactive repos
        inactive_repos = [
            {
                "url": "https://github.com/example/repo1",
                "days_inactive": 31,
                "last_push_date": thirty_one_days_ago.date().isoformat(),
                "visibility": "private",
            },
            {
                "url": "https://github.com/example/repo2",
                "days_inactive": 30,
                "last_push_date": thirty_days_ago.date().isoformat(),
                "visibility": "private",
            },
            {
                "url": "https://github.com/example/repo3",
                "days_inactive": 29,
                "last_push_date": twenty_nine_days_ago.date().isoformat(),
                "visibility": "public",
            },
        ]

        # Call the output_to_json function with the list of inactive repos
        expected_json = json.dumps(
            [
                {
                    "url": "https://github.com/example/repo1",
                    "daysInactive": 31,
                    "lastPushDate": thirty_one_days_ago.date().isoformat(),
                    "visibility": "private",
                },
                {
                    "url": "https://github.com/example/repo2",
                    "daysInactive": 30,
                    "lastPushDate": thirty_days_ago.date().isoformat(),
                    "visibility": "private",
                },
                {
                    "url": "https://github.com/example/repo3",
                    "daysInactive": 29,
                    "lastPushDate": twenty_nine_days_ago.date().isoformat(),
                    "visibility": "public",
                },
            ]
        )

        mock_file = MagicMock()
        # Check that the mock file object was called with the expected data
        expected_calls = [
            call.write(expected_json),
        ]

        output_to_json(inactive_repos, mock_file)
        mock_file.__enter__.return_value.assert_has_calls(expected_calls)


class TestIsRepoExempt(unittest.TestCase):
    """
    Test suite for the is_repo_exempt function.
    """

    def test_exempt_repos(self):
        """
        Test that a repo is exempt if its name is in the exempt_repos list.
        """
        repo = MagicMock(name="repo", spec=["name", "html_url"])
        exempt_topics = []

        test_cases = [
            ("exempt_repo", ["exempt_repo"], True),
            ("data-repo", ["data-*", "conf-*"], True),
            ("conf-repo", ["exempt_repo", "conf-*"], True),
            ("conf", ["conf-*"], False),
            ("repo", ["repo1", "repo-"], False),
            ("repo", [""], False),
        ]

        for repo_name, exempt_repos, expected_result in test_cases:
            with self.subTest(repo_name=repo_name, exempt_repos=exempt_repos):
                repo.name = repo_name
                repo.html_url = repo_name

                result = is_repo_exempt(repo, exempt_repos, exempt_topics)
                self.assertEqual(result, expected_result)

    def test_exempt_topics(self):
        """
        Test that a repo is exempt if one of its topics is in the exempt_topics list.
        """
        repo = MagicMock(name="repo", spec=["name", "html_url", "topics"])
        repo.name = "not_exempt_repo"
        repo.topics.return_value.names = ["exempt_topic"]
        exempt_repos = []
        exempt_topics = ["exempt_topic"]

        result = is_repo_exempt(repo, exempt_repos, exempt_topics)

        self.assertTrue(result)

    def test_not_exempt(self):
        """
        Test that a repo is not exempt if it is not in the exempt_repos
        list and none of its topics are in the exempt_topics list.
        """
        repo = MagicMock(name="repo", spec=["name", "html_url", "topics"])
        repo.name = "not_exempt_repo"
        repo.topics.return_value.names = ["not_exempt_topic"]
        exempt_repos = ["exempt_repo"]
        exempt_topics = ["exempt_topic"]

        result = is_repo_exempt(repo, exempt_repos, exempt_topics)

        self.assertFalse(result)

    def test_not_found_error(self):
        """
        Test that a repo is not exempt if a NotFoundError is raised
        which happens for private temporary forks.
        """
        repo = MagicMock(name="repo", spec=["name", "html_url", "topics"])
        repo.name = "not_exempt_repo"
        repo.topics.side_effect = github3.exceptions.NotFoundError(
            resp=MagicMock(status_code=404)
        )
        exempt_repos = []
        exempt_topics = ["exempt_topic"]

        result = is_repo_exempt(
            repo=repo, exempt_repos=exempt_repos, exempt_topics=exempt_topics
        )

        self.assertFalse(result)


class TestAdditionalMetrics(unittest.TestCase):
    """
    Test suite for verifying the correct calculation and inclusion of days since last release
    and last PR made in the report.
    """

    def test_days_since_last_release(self):
        """
        Test that the days since the last release
        is correctly calculated and included in the report.
        """
        # Mock repository with a release date 10 days ago
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        mock_repo = MagicMock()
        mock_repo.releases.return_value.__next__.return_value.created_at = (
            thirty_days_ago
        )

        # Calculate days since last release
        days_since_last_release = get_days_since_last_release(mock_repo)

        self.assertEqual(days_since_last_release, 30)

    def test_days_since_last_pr(self):
        """
        Test that the days since the last PR made
        is correctly calculated and included in the report.
        """
        # Mock repository with a PR date 20 days ago
        twenty_days_ago = datetime.now(timezone.utc) - timedelta(days=20)
        mock_repo = MagicMock()
        mock_repo.pull_requests.return_value.__next__.return_value.created_at = (
            twenty_days_ago
        )

        # Calculate days since last PR
        days_since_last_pr = get_days_since_last_pr(mock_repo)

        self.assertEqual(days_since_last_pr, 20)

    def test_report_inclusion_with_additional_metrics_configured(self):
        """
        Test that the report includes additional metrics when they are configured.
        """
        # Mock repository with a release date 10 days ago and a PR date 5 days ago
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        mock_repo = MagicMock(
            html_url="https://github.com/example/repo",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
        )
        mock_repo.releases.return_value.__next__.return_value.created_at = ten_days_ago
        mock_repo.pull_requests.return_value.__next__.return_value.created_at = (
            five_days_ago
        )

        # Mock GitHub connection
        mock_github = MagicMock()
        mock_github.organization.return_value.repositories.return_value = [mock_repo]

        # Generate report with additional metrics configured
        inactive_repos = get_inactive_repos(
            mock_github, 30, "example", ["release", "pr"]
        )

        # Check that the report includes the additional metrics
        expected_inactive_repos = [
            {
                "url": "https://github.com/example/repo",
                "days_inactive": 40,
                "last_push_date": forty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": 10,
                "days_since_last_pr": 5,
            },
        ]
        self.assertEqual(inactive_repos, expected_inactive_repos)

    def test_report_exclusion_with_additional_metrics_not_configured(self):
        """
        Test that the report excludes additional metrics when they are not configured.
        """
        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        mock_repo = MagicMock(
            html_url="https://github.com/example/repo",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
        )

        # Mock GitHub connection
        mock_github = MagicMock()
        mock_github.organization.return_value.repositories.return_value = [mock_repo]

        # Generate report without additional metrics configured
        inactive_repos = get_inactive_repos(mock_github, 30, "example", [])

        # Check that the report excludes the additional metrics
        expected_inactive_repos = [
            {
                "url": "https://github.com/example/repo",
                "days_inactive": 40,
                "last_push_date": forty_days_ago.date().isoformat(),
                "visibility": "private",
                "days_since_last_release": None,
                "days_since_last_pr": None,
            },
        ]
        self.assertEqual(inactive_repos, expected_inactive_repos)


class GetInactiveReposWithExemptReposTestCase(unittest.TestCase):
    """Verify get_inactive_repos honors the EXEMPT_REPOS environment variable."""

    def setUp(self):
        os.environ["EXEMPT_REPOS"] = "exempt_repo, another_exempt_repo"

    def tearDown(self):
        del os.environ["EXEMPT_REPOS"]

    def test_exempt_repos_env_var_is_parsed_and_applied(self):
        """EXEMPT_REPOS env var should exempt matching repos."""
        mock_github = MagicMock()
        mock_org = MagicMock()

        forty_days_ago = datetime.now(timezone.utc) - timedelta(days=40)
        exempt_repo = MagicMock(
            html_url="https://github.com/example/exempt_repo",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        exempt_repo.name = "exempt_repo"
        exempt_repo.topics.return_value.names = []

        included_repo = MagicMock(
            html_url="https://github.com/example/included_repo",
            pushed_at=forty_days_ago.isoformat(),
            archived=False,
            private=True,
        )
        included_repo.name = "included_repo"
        included_repo.topics.return_value.names = []

        mock_github.organization.return_value = mock_org
        mock_org.repositories.return_value = [exempt_repo, included_repo]

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            inactive_repos = get_inactive_repos(mock_github, 30, "example")
            output = mock_stdout.getvalue()

        self.assertIn("Exempt repos: ['exempt_repo', 'another_exempt_repo']", output)
        self.assertEqual(len(inactive_repos), 1)
        self.assertEqual(
            inactive_repos[0]["url"], "https://github.com/example/included_repo"
        )


class GetDaysSinceLastReleaseExceptionTestCase(unittest.TestCase):
    """Cover the exception branches in get_days_since_last_release."""

    def test_returns_none_on_type_error(self):
        """A TypeError on the release iterator should return None and log a message."""
        mock_repo = MagicMock(html_url="https://github.com/example/repo")
        mock_repo.releases.return_value.__next__.side_effect = TypeError(
            "ghost user release"
        )

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = get_days_since_last_release(mock_repo)
            output = mock_stdout.getvalue()

        self.assertIsNone(result)
        self.assertIn(
            "https://github.com/example/repo had an exception trying to get the last release",
            output,
        )

    def test_returns_none_when_no_releases(self):
        """If the releases iterator is empty, return None without raising."""
        mock_repo = MagicMock()
        mock_repo.releases.return_value.__next__.side_effect = StopIteration

        result = get_days_since_last_release(mock_repo)

        self.assertIsNone(result)


class GetDaysSinceLastPrExceptionTestCase(unittest.TestCase):
    """Cover the exception branches in get_days_since_last_pr."""

    def test_returns_none_when_no_pull_requests(self):
        """If the pull_requests iterator is empty, return None without raising."""
        mock_repo = MagicMock()
        mock_repo.pull_requests.return_value.__next__.side_effect = StopIteration

        result = get_days_since_last_pr(mock_repo)

        self.assertIsNone(result)


class GetActiveDateUnsupportedMethodTestCase(unittest.TestCase):
    """Cover the ValueError branch in get_active_date when ACTIVITY_METHOD is bogus."""

    @patch.dict(os.environ, {"ACTIVITY_METHOD": "not_a_real_method"})
    def test_unsupported_activity_method_raises_value_error(self):
        """Unsupported ACTIVITY_METHOD should raise ValueError (the raise sits
        outside the github3 exception handler, so it propagates to the caller)."""
        repo = MagicMock(html_url="https://github.com/example/repo")
        with self.assertRaises(ValueError) as ctx:
            get_active_date(repo)
        self.assertIn(
            "ACTIVITY_METHOD environment variable has unsupported value",
            str(ctx.exception),
        )


class OutputToJsonOptionalKeysTestCase(unittest.TestCase):
    """Cover the optional release/pr key branches in output_to_json."""

    def test_includes_release_and_pr_keys_when_present(self):
        """When repo_data dicts include 'release' and 'pr' marker keys, the JSON
        output must include the additional daysSinceLastRelease and
        daysSinceLastPR fields."""
        inactive_repos = [
            {
                "url": "https://github.com/example/repo",
                "days_inactive": 40,
                "last_push_date": "2024-01-01",
                "visibility": "public",
                "release": True,
                "days_since_last_release": 5,
                "pr": True,
                "days_since_last_pr": 2,
            }
        ]

        result_json = output_to_json(inactive_repos, MagicMock())
        result = json.loads(result_json)

        self.assertEqual(result[0]["daysSinceLastRelease"], 5)
        self.assertEqual(result[0]["daysSinceLastPR"], 2)


class OutputToJsonGithubOutputTestCase(unittest.TestCase):
    """Cover the GITHUB_OUTPUT environment variable branch in output_to_json."""

    def test_writes_to_github_output_when_env_var_set(self):
        """When GITHUB_OUTPUT is set, output_to_json should append a
        `inactiveRepos=` line to the file path it points at."""
        inactive_repos = [
            {
                "url": "https://github.com/example/repo",
                "days_inactive": 40,
                "last_push_date": "2024-01-01",
                "visibility": "public",
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".out"
        ) as github_output_file:
            github_output_path = github_output_file.name

        try:
            with patch.dict(os.environ, {"GITHUB_OUTPUT": github_output_path}):
                output_to_json(inactive_repos, MagicMock())

            with open(github_output_path, "r", encoding="utf-8") as handle:
                contents = handle.read()
            self.assertIn("inactiveRepos=", contents)
            self.assertIn("https://github.com/example/repo", contents)
        finally:
            os.remove(github_output_path)


class SetRepoDataGithubExceptionTestCase(unittest.TestCase):
    """Cover the GitHubException branches in set_repo_data."""

    def test_github_exception_on_release_is_logged(self):
        """A GitHubException raised when fetching releases should be caught and
        logged; days_since_last_release should stay None."""
        repo = MagicMock(html_url="https://github.com/example/repo")
        repo.releases.side_effect = github3.exceptions.GitHubException("release boom")

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = set_repo_data(repo, 10, "2024-01-01", "public", ["release"])
            output = mock_stdout.getvalue()

        self.assertIsNone(result["days_since_last_release"])
        self.assertIn(
            "https://github.com/example/repo had an exception trying to get the last release",
            output,
        )

    def test_github_exception_on_pr_is_logged(self):
        """A GitHubException raised when fetching PRs should be caught and
        logged; days_since_last_pr should stay None."""
        repo = MagicMock(html_url="https://github.com/example/repo")
        repo.pull_requests.side_effect = github3.exceptions.GitHubException("pr boom")

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            result = set_repo_data(repo, 10, "2024-01-01", "public", ["pr"])
            output = mock_stdout.getvalue()

        self.assertIsNone(result["days_since_last_pr"])
        self.assertIn(
            "https://github.com/example/repo had an exception trying to get the last PR",
            output,
        )
