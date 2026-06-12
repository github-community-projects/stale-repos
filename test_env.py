"""A module containing unit tests for the config module functions.

Classes:
    TestGetIntFromEnv: A class to test the get_int_env_var function.
    TestEnvVars: A class to test the get_env_vars function.

"""

import os
import unittest
from unittest.mock import patch

from env import EnvVars, get_env_vars

TOKEN = "test_token"


class TestGetEnvVars(unittest.TestCase):
    """
    Test suite for the get_env_vars function.
    """

    def setUp(self):
        env_keys = [
            "GH_APP_ID",
            "GH_APP_INSTALLATION_ID",
            "GH_APP_PRIVATE_KEY",
            "GH_TOKEN",
            "GHE",
            "SKIP_EMPTY_REPORTS",
        ]
        for key in env_keys:
            if key in os.environ:
                del os.environ[key]

    @patch.dict(
        os.environ,
        {
            "GH_APP_ID": "12345",
            "GH_APP_INSTALLATION_ID": "678910",
            "GH_APP_PRIVATE_KEY": "hello",
            "GH_TOKEN": "",
            "GH_ENTERPRISE_URL": "",
        },
        clear=True,
    )
    def test_get_env_vars_with_github_app(self):
        """Test that all environment variables are set correctly using GitHub App"""
        expected_result = EnvVars(
            gh_app_id=12345,
            gh_app_installation_id=678910,
            gh_app_private_key_bytes=b"hello",
            gh_app_enterprise_only=False,
            gh_token="",
            ghe="",
            skip_empty_reports=True,
            workflow_summary_enabled=False,
        )
        result = get_env_vars(True)
        self.assertEqual(str(result), str(expected_result))

    @patch.dict(
        os.environ,
        {
            "GH_APP_ID": "",
            "GH_APP_INSTALLATION_ID": "",
            "GH_APP_PRIVATE_KEY": "",
            "GH_ENTERPRISE_URL": "",
            "GH_TOKEN": TOKEN,
        },
        clear=True,
    )
    def test_get_env_vars_with_token(self):
        """Test that all environment variables are set correctly using a list of repositories"""
        expected_result = EnvVars(
            gh_app_id=None,
            gh_app_installation_id=None,
            gh_app_private_key_bytes=b"",
            gh_app_enterprise_only=False,
            gh_token=TOKEN,
            ghe="",
            skip_empty_reports=True,
            workflow_summary_enabled=False,
        )
        result = get_env_vars(True)
        self.assertEqual(str(result), str(expected_result))

    @patch.dict(
        os.environ,
        {
            "GH_APP_ID": "",
            "GH_APP_INSTALLATION_ID": "",
            "GH_APP_PRIVATE_KEY": "",
            "GH_TOKEN": "",
        },
        clear=True,
    )
    def test_get_env_vars_missing_token(self):
        """Test that an error is raised if the TOKEN environment variables is not set"""
        with self.assertRaises(ValueError):
            get_env_vars(True)

    @patch.dict(
        os.environ,
        {
            "GH_APP_ID": "",
            "GH_APP_INSTALLATION_ID": "",
            "GH_APP_PRIVATE_KEY": "",
            "GH_TOKEN": TOKEN,
            "GH_ENTERPRISE_URL": "",
            "SKIP_EMPTY_REPORTS": "false",
        },
    )
    def test_get_env_vars_optional_values(self):
        """Test that optional values are set when provided"""
        expected_result = EnvVars(
            gh_app_id=None,
            gh_app_installation_id=None,
            gh_app_private_key_bytes=b"",
            gh_app_enterprise_only=False,
            gh_token=TOKEN,
            ghe="",
            skip_empty_reports=False,
            workflow_summary_enabled=False,
        )
        result = get_env_vars(True)
        self.assertEqual(str(result), str(expected_result))

    @patch.dict(
        os.environ,
        {
            "GH_APP_ID": "",
            "GH_APP_INSTALLATION_ID": "",
            "GH_APP_PRIVATE_KEY": "",
            "GH_TOKEN": "TOKEN",
        },
        clear=True,
    )
    def test_get_env_vars_optionals_are_defaulted(self):
        """Test that optional values are set to their default values if not provided"""
        expected_result = EnvVars(
            gh_app_id=None,
            gh_app_installation_id=None,
            gh_app_private_key_bytes=b"",
            gh_app_enterprise_only=False,
            gh_token="TOKEN",
            ghe=None,
            skip_empty_reports=True,
            workflow_summary_enabled=False,
        )
        result = get_env_vars(True)
        self.assertEqual(str(result), str(expected_result))

    @patch.dict(
        os.environ,
        {
            "ORGANIZATION": "my_organization",
            "GH_APP_ID": "12345",
            "GH_APP_INSTALLATION_ID": "",
            "GH_APP_PRIVATE_KEY": "",
            "GH_TOKEN": "",
        },
        clear=True,
    )
    def test_get_env_vars_auth_with_github_app_installation_missing_inputs(self):
        """Test that an error is raised there are missing inputs for the gh app"""
        with self.assertRaises(ValueError) as context_manager:
            get_env_vars(True)
        the_exception = context_manager.exception
        self.assertEqual(
            str(the_exception),
            "GH_APP_ID set and GH_APP_INSTALLATION_ID or GH_APP_PRIVATE_KEY variable not set",
        )

    @patch.dict(
        os.environ,
        {
            "GH_TOKEN": "TOKEN",
            "WORKFLOW_SUMMARY_ENABLED": "true",
        },
        clear=True,
    )
    def test_get_env_vars_with_workflow_summary_enabled(self):
        """Test that workflow_summary_enabled is set to True when environment variable is true"""
        expected_result = EnvVars(
            gh_app_id=None,
            gh_app_installation_id=None,
            gh_app_private_key_bytes=b"",
            gh_app_enterprise_only=False,
            gh_token="TOKEN",
            ghe=None,
            skip_empty_reports=True,
            workflow_summary_enabled=True,
        )
        result = get_env_vars(True)
        self.assertEqual(str(result), str(expected_result))

    @patch.dict(
        os.environ,
        {"GH_TOKEN": "TOKEN"},
        clear=True,
    )
    @patch("env.load_dotenv")
    def test_get_env_vars_loads_dotenv_when_not_test(self, mock_load_dotenv):
        """Test that get_env_vars loads the .env file when test is False."""
        get_env_vars(test=False)
        mock_load_dotenv.assert_called_once()


if __name__ == "__main__":
    unittest.main()
