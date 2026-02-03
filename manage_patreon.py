"""
Utility script to manage Patreon supporter status for users.

Usage:
    python manage_patreon.py list
    python manage_patreon.py set <username> <tier>
    python manage_patreon.py remove <username>
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.extensions import db
from app.models import User


def list_supporters():
    """List all users with Patreon supporter status."""
    app = create_app()
    with app.app_context():
        supporters = User.query.filter_by(is_patreon_supporter=True).all()
        if not supporters:
            print("No Patreon supporters found.")
            return

        print("\nPatreon Supporters:")
        print("-" * 70)
        for user in supporters:
            print(
                f"Username: {user.username:20} | Tier: {user.patreon_tier or 'N/A':15} | ID: {user.patreon_id or 'N/A'}"
            )
        print()


def set_supporter(username: str, tier: str = "supporter"):
    """Set a user as a Patreon supporter."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            return

        user.is_patreon_supporter = True
        user.patreon_tier = tier
        db.session.commit()

        print(f"✓ User '{username}' is now a Patreon supporter with tier '{tier}'.")


def remove_supporter(username: str):
    """Remove Patreon supporter status from a user."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            return

        user.is_patreon_supporter = False
        user.patreon_tier = None
        user.patreon_id = None
        db.session.commit()

        print(f"✓ Patreon supporter status removed from user '{username}'.")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_supporters()
    elif command == "set":
        if len(sys.argv) < 3:
            print("Error: Username required.")
            print("Usage: python manage_patreon.py set <username> [tier]")
            sys.exit(1)
        username = sys.argv[2]
        tier = sys.argv[3] if len(sys.argv) > 3 else "supporter"
        set_supporter(username, tier)
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Error: Username required.")
            print("Usage: python manage_patreon.py remove <username>")
            sys.exit(1)
        username = sys.argv[2]
        remove_supporter(username)
    else:
        print(f"Error: Unknown command '{command}'")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
