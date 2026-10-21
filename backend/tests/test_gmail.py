"""
Tests for Gmail client wrapper.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.gmail import GmailClient

@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_init(mock_creds, mock_build):
    client = GmailClient(
        access_token="fake_token",
        refresh_token="fake_refresh",
        client_id="fake_id",
        client_secret="fake_secret"
    )
    assert client is not None
    mock_build.assert_called_once()
