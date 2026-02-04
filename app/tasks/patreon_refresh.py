"""
Scheduled task for refreshing Patreon OAuth tokens.

This task runs periodically to ensure Patreon access tokens remain valid
by refreshing them before they expire.
"""

import logging

logger = logging.getLogger(__name__)


def refresh_patreon_token(app=None):
    """Refresh Patreon access token if it's expiring soon.

    This task checks if the Patreon access token will expire within 5 minutes
    and refreshes it if necessary. The new token is automatically saved to
    the secrets.json configuration file.

    Args:
        app: Flask application instance. If None, will try to get from current context.
    """
    if app is None:
        from flask import current_app

        try:
            app = current_app._get_current_object()  # type: ignore
        except RuntimeError:
            logging.error(
                "refresh_patreon_token called outside application context and no app provided"
            )
            return

    with app.app_context():
        from app.services.patreon_client import (
            PatreonTokenExpiredError,
            get_patreon_client,
            is_patreon_configured,
        )

        try:
            # Check if Patreon is configured
            if not is_patreon_configured():
                logger.debug("Patreon not configured, skipping token refresh")
                return

            # Get client (this will automatically refresh token if needed)
            client = get_patreon_client()

            # Force a check of token validity
            if client._is_token_expiring_soon():
                logger.info("Patreon token refresh check triggered by scheduled task")
                client._ensure_token_valid()
            else:
                logger.debug("Patreon token is still valid")

        except PatreonTokenExpiredError as e:
            logger.error(f"Failed to refresh Patreon token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Patreon token refresh: {e}")
