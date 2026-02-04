"""
Patreon API client with automatic token refresh.

This service manages Patreon OAuth2 tokens stored in secrets.json and
automatically refreshes them when they expire within 5 minutes.

The Patreon integration uses machine-to-machine (M2M) OAuth2 flow with
refresh tokens to maintain persistent API access.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from app.config import load_secrets, save_secrets

logger = logging.getLogger(__name__)


class PatreonTokenExpiredError(Exception):
    """Raised when Patreon token is expired and refresh fails."""


class PatreonClient:
    """Client for Patreon API with automatic token refresh.

    This client manages OAuth2 tokens and automatically refreshes them
    when they're about to expire (within 5 minutes).

    Configuration is stored in secrets.json with the following keys:
    - patreon_client_id: OAuth2 client ID
    - patreon_client_secrete: OAuth2 client secret
    - patreon_access_token: Current access token
    - patreon_refresh_token: Refresh token for obtaining new access tokens
    - patreon_expires_at: ISO 8601 timestamp when token expires

    Example secrets.json:
    {
        "patreon_client_id": "your_client_id",
        "patreon_client_secrete": "your_client_secrete",
        "patreon_access_token": "your_access_token",
        "patreon_refresh_token": "your_refresh_token",
        "patreon_expires_at": "2026-02-14T12:13:46.508421+00:00"
    }
    """

    TOKEN_REFRESH_URL = "https://www.patreon.com/api/oauth2/token"
    API_BASE_URL = "https://www.patreon.com/api/oauth2/v2"

    # Refresh token if it expires within 5 minutes
    REFRESH_THRESHOLD = timedelta(minutes=5)

    def __init__(self):
        """Initialize Patreon client and ensure token is valid."""
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None

        self._load_config()
        self._ensure_token_valid()

    def _load_config(self) -> None:
        """Load Patreon configuration from secrets.json."""
        secrets = load_secrets()

        self._client_id = secrets.get("patreon_client_id")
        self._client_secret = secrets.get("patreon_client_secrete")
        self._access_token = secrets.get("patreon_access_token")
        self._refresh_token = secrets.get("patreon_refresh_token")

        expires_at_str = secrets.get("patreon_expires_at")
        if expires_at_str:
            try:
                self._expires_at = datetime.fromisoformat(expires_at_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid patreon_expires_at format: {expires_at_str}")
                self._expires_at = None

    def _save_config(self) -> None:
        """Save Patreon configuration to secrets.json."""
        secrets = load_secrets()

        secrets["patreon_client_id"] = self._client_id
        secrets["patreon_client_secrete"] = self._client_secret
        secrets["patreon_access_token"] = self._access_token
        secrets["patreon_refresh_token"] = self._refresh_token

        if self._expires_at:
            secrets["patreon_expires_at"] = self._expires_at.isoformat()

        save_secrets(secrets)
        logger.info("Patreon configuration saved to secrets.json")

    def _is_token_expiring_soon(self) -> bool:
        """Check if token will expire within the refresh threshold.

        Returns:
            True if token expires within 5 minutes or is already expired
        """
        if not self._expires_at:
            return True

        now = datetime.now(UTC)
        # Make expires_at timezone-aware if it isn't already
        if self._expires_at.tzinfo is None:
            expires_at = self._expires_at.replace(tzinfo=UTC)
        else:
            expires_at = self._expires_at

        return (expires_at - now) <= self.REFRESH_THRESHOLD

    def _ensure_token_valid(self) -> None:
        """Ensure access token is valid, refresh if necessary."""
        if not self._is_configured():
            logger.debug("Patreon not configured, skipping token validation")
            return

        if self._is_token_expiring_soon():
            logger.info("Patreon token expiring soon, refreshing...")
            self._refresh_access_token()

    def _is_configured(self) -> bool:
        """Check if Patreon credentials are configured.

        Returns:
            True if all required credentials are present
        """
        return bool(self._client_id and self._client_secret and self._refresh_token)

    def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token.

        Raises:
            PatreonTokenExpiredError: If token refresh fails
        """
        if not self._refresh_token:
            raise PatreonTokenExpiredError("No refresh token available")

        try:
            response = requests.post(
                self.TOKEN_REFRESH_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Update tokens
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)

            # Calculate expiry time
            expires_in = data.get("expires_in", 2592000)  # Default 30 days
            self._expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

            # Save updated configuration
            self._save_config()

            logger.info("Patreon access token refreshed successfully")

        except requests.RequestException as e:
            logger.error(f"Failed to refresh Patreon token: {e}")
            raise PatreonTokenExpiredError(f"Token refresh failed: {e}") from e
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid token refresh response: {e}")
            raise PatreonTokenExpiredError(f"Invalid response: {e}") from e

    def is_configured(self) -> bool:
        """Check if Patreon integration is properly configured.

        Returns:
            True if all required credentials are configured
        """
        return self._is_configured()

    def get_campaign_members(self, campaign_id: str) -> list[dict[str, Any]]:
        """Get list of campaign members (patrons).

        Args:
            campaign_id: The Patreon campaign ID

        Returns:
            List of patron data dictionaries

        Raises:
            PatreonTokenExpiredError: If token is invalid and refresh fails
        """
        self._ensure_token_valid()

        if not self._access_token:
            raise PatreonTokenExpiredError("No access token available")

        try:
            url = f"{self.API_BASE_URL}/campaigns/{campaign_id}/members"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
            }
            params = {
                "include": "user,currently_entitled_tiers",
                "fields[member]": "full_name,patron_status,currently_entitled_amount_cents,last_charge_status",
                "fields[tier]": "title,amount_cents",
                "fields[user]": "email,full_name",
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Patreon campaign members: {e}")
            raise

    def get_member_info(self, member_id: str) -> dict[str, Any]:
        """Get information about a specific campaign member.

        Args:
            member_id: The Patreon member ID

        Returns:
            Member data dictionary

        Raises:
            PatreonTokenExpiredError: If token is invalid and refresh fails
        """
        self._ensure_token_valid()

        if not self._access_token:
            raise PatreonTokenExpiredError("No access token available")

        try:
            url = f"{self.API_BASE_URL}/members/{member_id}"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
            }
            params = {
                "include": "user,currently_entitled_tiers",
                "fields[member]": "full_name,patron_status,currently_entitled_amount_cents",
                "fields[tier]": "title,amount_cents",
                "fields[user]": "email,full_name",
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Patreon member info: {e}")
            raise


# Singleton instance
_patreon_client = None


def get_patreon_client() -> PatreonClient:
    """Get the singleton Patreon client instance.

    Returns:
        PatreonClient instance with valid tokens
    """
    global _patreon_client
    if _patreon_client is None:
        _patreon_client = PatreonClient()
    return _patreon_client


def is_patreon_configured() -> bool:
    """Check if Patreon integration is configured.

    Returns:
        True if Patreon credentials are present in secrets.json
    """
    try:
        client = get_patreon_client()
        return client.is_configured()
    except Exception as e:
        logger.debug(f"Patreon not configured: {e}")
        return False
