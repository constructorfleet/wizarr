#!/usr/bin/env python3
"""
Example script demonstrating Patreon token management.

This script shows how to:
1. Configure Patreon credentials
2. Check token status
3. Manually trigger a refresh
4. Fetch campaign members

Usage:
    python examples/patreon_example.py
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.config import load_secrets, save_secrets
from app.services.patreon_client import (
    PatreonTokenExpiredError,
    get_patreon_client,
    is_patreon_configured,
)


def setup_example_config():
    """Setup example Patreon configuration (replace with real values)."""
    print("Setting up example Patreon configuration...")
    print("NOTE: Replace these values with real credentials!\n")

    secrets = load_secrets()

    # Example configuration - REPLACE WITH REAL VALUES
    secrets["patreon_client_id"] = "your_client_id_here"
    secrets["patreon_client_secrete"] = "your_client_secret_here"
    secrets["patreon_access_token"] = "your_access_token_here"
    secrets["patreon_refresh_token"] = "your_refresh_token_here"
    # Set expiry to 2 minutes from now to demonstrate automatic refresh
    secrets["patreon_expires_at"] = (
        datetime.now(UTC) + timedelta(minutes=2)
    ).isoformat()

    save_secrets(secrets)
    print("✓ Configuration saved to secrets.json")
    print("  (Token set to expire in 2 minutes to demonstrate refresh)\n")


def check_configuration():
    """Check if Patreon is configured."""
    print("Checking Patreon configuration...")

    if is_patreon_configured():
        print("✓ Patreon is configured\n")
        return True
    else:
        print("✗ Patreon is not configured")
        print("  Run with --setup to create example configuration\n")
        return False


def check_token_status():
    """Check current token status."""
    print("Checking token status...")

    try:
        client = get_patreon_client()

        print(f"  Client ID: {client._client_id}")
        print(f"  Has access token: {bool(client._access_token)}")
        print(f"  Has refresh token: {bool(client._refresh_token)}")

        if client._expires_at:
            now = datetime.now(UTC)
            expires_at = client._expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)

            time_until_expiry = expires_at - now
            print(f"  Token expires: {expires_at.isoformat()}")
            print(f"  Time until expiry: {time_until_expiry}")

            if time_until_expiry <= timedelta(minutes=5):
                print("  ⚠ Token will expire within 5 minutes - refresh triggered!")
            else:
                print("  ✓ Token is valid")
        else:
            print("  ⚠ No expiry time set")

        print()

    except PatreonTokenExpiredError as e:
        print(f"✗ Token expired: {e}\n")
    except Exception as e:
        print(f"✗ Error checking token: {e}\n")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Patreon Token Management Example")
    print("=" * 60)
    print()

    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_example_config()
        return

    # Create app context
    app = create_app()

    with app.app_context():
        # Check configuration
        if not check_configuration():
            print("Run with --setup to create example configuration:")
            print("  python examples/patreon_example.py --setup")
            return

        # Check token status
        check_token_status()

        print("=" * 60)
        print("Example complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()
