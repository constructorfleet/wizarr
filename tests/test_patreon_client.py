"""Tests for Patreon client token management."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from app.services.patreon_client import (
    PatreonClient,
    PatreonTokenExpiredError,
    get_patreon_client,
    is_patreon_configured,
)


@pytest.fixture
def temp_secrets_file():
    """Create a temporary secrets file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        secrets = {
            "patreon_client_id": "test_client_id",
            "patreon_client_secrete": "test_client_secret",
            "patreon_access_token": "test_access_token",
            "patreon_refresh_token": "test_refresh_token",
            "patreon_expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        json.dump(secrets, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_secrets_file(temp_secrets_file):
    """Mock the SECRETS_FILE path to use temporary file."""
    with patch("app.services.patreon_client.load_secrets") as mock_load:
        with patch("app.services.patreon_client.save_secrets") as mock_save:
            # Load actual secrets from temp file
            with open(temp_secrets_file) as f:
                secrets = json.load(f)
            mock_load.return_value = secrets

            # Mock save to update the dict
            def save_side_effect(new_secrets):
                secrets.update(new_secrets)

            mock_save.side_effect = save_side_effect

            yield secrets


class TestPatreonClient:
    """Test suite for PatreonClient."""

    def test_load_config(self, mock_secrets_file):
        """Test loading Patreon configuration from secrets."""
        client = PatreonClient()

        assert client._client_id == "test_client_id"
        assert client._client_secret == "test_client_secret"
        assert client._access_token == "test_access_token"
        assert client._refresh_token == "test_refresh_token"
        assert client._expires_at is not None

    def test_is_configured(self, mock_secrets_file):
        """Test checking if Patreon is configured."""
        client = PatreonClient()
        assert client.is_configured() is True

    def test_is_not_configured_missing_client_id(self, mock_secrets_file):
        """Test configuration check when client_id is missing."""
        mock_secrets_file["patreon_client_id"] = None

        client = PatreonClient()
        assert client.is_configured() is False

    def test_is_token_expiring_soon_within_threshold(self, mock_secrets_file):
        """Test token expiring within 5 minutes threshold."""
        # Set expiry to 3 minutes from now
        expires_at = datetime.now(UTC) + timedelta(minutes=3)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        client = PatreonClient()
        assert client._is_token_expiring_soon() is True

    def test_is_token_not_expiring_soon(self, mock_secrets_file):
        """Test token not expiring within threshold."""
        # Set expiry to 10 minutes from now
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        client = PatreonClient()
        assert client._is_token_expiring_soon() is False

    def test_is_token_already_expired(self, mock_secrets_file):
        """Test already expired token."""
        # Set expiry to 1 hour ago
        expires_at = datetime.now(UTC) - timedelta(hours=1)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        client = PatreonClient()
        assert client._is_token_expiring_soon() is True

    @patch("app.services.patreon_client.requests.post")
    def test_refresh_access_token_success(self, mock_post, mock_secrets_file):
        """Test successful token refresh."""
        # Set token to expire soon to trigger refresh
        expires_at = datetime.now(UTC) + timedelta(minutes=2)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        # Mock successful refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 2592000,  # 30 days
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PatreonClient()

        # Verify token was refreshed
        assert client._access_token == "new_access_token"
        assert client._refresh_token == "new_refresh_token"
        assert client._expires_at is not None

        # Verify API was called with correct parameters
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["data"]["grant_type"] == "refresh_token"
        assert call_kwargs["data"]["client_id"] == "test_client_id"
        assert call_kwargs["data"]["client_secret"] == "test_client_secret"

    @patch("app.services.patreon_client.requests.post")
    def test_refresh_access_token_failure(self, mock_post, mock_secrets_file):
        """Test failed token refresh."""
        # Set token to expire soon
        expires_at = datetime.now(UTC) + timedelta(minutes=2)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        # Mock failed refresh response
        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(PatreonTokenExpiredError):
            PatreonClient()

    @patch("app.services.patreon_client.requests.post")
    def test_refresh_preserves_refresh_token(self, mock_post, mock_secrets_file):
        """Test that refresh token is preserved if not in response."""
        expires_at = datetime.now(UTC) + timedelta(minutes=2)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        # Mock response without new refresh token
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 2592000,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PatreonClient()

        # Verify original refresh token is preserved
        assert client._refresh_token == "test_refresh_token"

    @patch("app.services.patreon_client.requests.post")
    def test_save_config_after_refresh(self, mock_post, mock_secrets_file):
        """Test that configuration is saved after token refresh."""
        expires_at = datetime.now(UTC) + timedelta(minutes=2)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 2592000,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with patch("app.services.patreon_client.save_secrets") as mock_save:
            client = PatreonClient()

            # Verify save was called
            assert mock_save.called

            # Verify saved data contains new tokens
            saved_data = mock_save.call_args[0][0]
            assert saved_data["patreon_access_token"] == "new_access_token"
            assert saved_data["patreon_refresh_token"] == "new_refresh_token"
            assert "patreon_expires_at" in saved_data

    @patch("app.services.patreon_client.requests.get")
    def test_get_campaign_members(self, mock_get, mock_secrets_file):
        """Test fetching campaign members."""
        # Set token to not expire soon
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "member1",
                    "type": "member",
                    "attributes": {"full_name": "John Doe"},
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PatreonClient()
        members = client.get_campaign_members("campaign123")

        assert len(members) == 1
        assert members[0]["id"] == "member1"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "campaign123" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token"

    @patch("app.services.patreon_client.requests.get")
    def test_get_member_info(self, mock_get, mock_secrets_file):
        """Test fetching individual member info."""
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "id": "member1",
                "type": "member",
                "attributes": {"full_name": "Jane Doe"},
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PatreonClient()
        member_info = client.get_member_info("member1")

        assert member_info["data"]["id"] == "member1"

    def test_invalid_expires_at_format(self, mock_secrets_file):
        """Test handling of invalid expires_at format."""
        mock_secrets_file["patreon_expires_at"] = "invalid_date"

        client = PatreonClient()
        # Should default to None and trigger refresh
        assert client._expires_at is None

    def test_timezone_aware_expiry_check(self, mock_secrets_file):
        """Test that expiry check handles timezone-aware dates correctly."""
        # Use explicit timezone-aware datetime
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        client = PatreonClient()
        assert client._is_token_expiring_soon() is False


class TestPatreonClientHelpers:
    """Test helper functions for Patreon client."""

    @patch("app.services.patreon_client.PatreonClient")
    def test_get_patreon_client_singleton(self, mock_client_class):
        """Test that get_patreon_client returns singleton instance."""
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        # Import after patching to reset singleton
        from importlib import reload

        import app.services.patreon_client as pc

        reload(pc)

        client1 = pc.get_patreon_client()
        client2 = pc.get_patreon_client()

        assert client1 is client2

    def test_is_patreon_configured_true(self, mock_secrets_file):
        """Test is_patreon_configured returns True when configured."""
        result = is_patreon_configured()
        assert result is True

    def test_is_patreon_configured_false(self):
        """Test is_patreon_configured returns False when not configured."""
        with patch("app.services.patreon_client.load_secrets") as mock_load:
            mock_load.return_value = {}
            result = is_patreon_configured()
            assert result is False

    @patch("app.services.patreon_client.requests.post")
    def test_automatic_refresh_on_api_call(self, mock_post, mock_secrets_file):
        """Test that token is automatically refreshed before API calls."""
        # Set token to expire in 2 minutes
        expires_at = datetime.now(UTC) + timedelta(minutes=2)
        mock_secrets_file["patreon_expires_at"] = expires_at.isoformat()

        # Mock refresh response
        mock_refresh_response = Mock()
        mock_refresh_response.json.return_value = {
            "access_token": "refreshed_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 2592000,
        }
        mock_refresh_response.raise_for_status = Mock()
        mock_post.return_value = mock_refresh_response

        # Mock API GET request
        with patch("app.services.patreon_client.requests.get") as mock_get:
            mock_get_response = Mock()
            mock_get_response.json.return_value = {"data": []}
            mock_get_response.raise_for_status = Mock()
            mock_get.return_value = mock_get_response

            client = PatreonClient()
            client.get_campaign_members("campaign123")

            # Verify refresh was called
            assert mock_post.called
            # Verify API call used refreshed token
            call_args = mock_get.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer refreshed_token"
