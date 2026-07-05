"""Test cases for the auth module."""

import unittest
from unittest.mock import MagicMock, patch

import auth


class TestAuth(unittest.TestCase):
    """
    Test case for the auth module.
    """

    @patch("auth.Github")
    @patch("auth.Auth")
    def test_auth_to_github_with_token(self, mock_auth, mock_github):
        """
        Test the auth_to_github function when the token is provided.
        """
        mock_token = MagicMock()
        mock_auth.Token.return_value = mock_token
        mock_github.return_value = "Authenticated to GitHub.com"

        result = auth.auth_to_github("token", None, None, b"", None, False)

        mock_auth.Token.assert_called_once_with("token")
        mock_github.assert_called_once_with(auth=mock_token)
        self.assertEqual(result, "Authenticated to GitHub.com")

    def test_auth_to_github_without_token(self):
        """
        Test the auth_to_github function when the token is not provided.
        Expect a ValueError to be raised.
        """
        with self.assertRaises(ValueError) as context_manager:
            auth.auth_to_github("", None, None, b"", None, False)
        the_exception = context_manager.exception
        self.assertEqual(
            str(the_exception),
            "GH_TOKEN or the set of [GH_APP_ID, GH_APP_INSTALLATION_ID, GH_APP_PRIVATE_KEY] environment variables are not set",
        )

    @patch("auth.Github")
    @patch("auth.Auth")
    def test_auth_to_github_with_ghe(self, mock_auth, mock_github):
        """
        Test the auth_to_github function when the GitHub Enterprise URL is provided.
        """
        mock_token = MagicMock()
        mock_auth.Token.return_value = mock_token
        mock_github.return_value = "Authenticated to GitHub Enterprise"
        result = auth.auth_to_github(
            "token", None, None, b"", "https://github.example.com", False
        )

        mock_auth.Token.assert_called_once_with("token")
        mock_github.assert_called_once_with(
            base_url="https://github.example.com/api/v3", auth=mock_token
        )
        self.assertEqual(result, "Authenticated to GitHub Enterprise")

    @patch("auth.Github")
    @patch("auth.Auth")
    def test_auth_to_github_with_ghe_and_ghe_app(self, mock_auth, mock_github):
        """
        Test the auth_to_github function when the GitHub Enterprise URL is provided and the app was created in GitHub Enterprise URL.
        """
        mock_app_auth = MagicMock()
        mock_installation_auth = MagicMock()
        mock_auth.AppAuth.return_value = mock_app_auth
        mock_app_auth.get_installation_auth.return_value = mock_installation_auth
        mock_github.return_value = MagicMock()

        result = auth.auth_to_github(
            "", 123, 456, b"private_key", "https://github.example.com", True
        )

        mock_auth.AppAuth.assert_called_once_with(123, "private_key")
        mock_app_auth.get_installation_auth.assert_called_once_with(456)
        mock_github.assert_called_once_with(
            base_url="https://github.example.com/api/v3",
            auth=mock_installation_auth,
        )
        self.assertEqual(result, mock_github.return_value)

    @patch("auth.Github")
    @patch("auth.Auth")
    def test_auth_to_github_with_app(self, mock_auth, mock_github):
        """
        Test the auth_to_github function when app credentials are provided
        """
        mock_app_auth = MagicMock()
        mock_installation_auth = MagicMock()
        mock_auth.AppAuth.return_value = mock_app_auth
        mock_app_auth.get_installation_auth.return_value = mock_installation_auth
        mock_github.return_value = MagicMock()

        result = auth.auth_to_github(
            "", 123, 456, b"private_key", "https://github.example.com", False
        )

        mock_auth.AppAuth.assert_called_once_with(123, "private_key")
        mock_app_auth.get_installation_auth.assert_called_once_with(456)
        mock_github.assert_called_once_with(auth=mock_installation_auth)
        self.assertEqual(result, mock_github.return_value)


if __name__ == "__main__":
    unittest.main()
