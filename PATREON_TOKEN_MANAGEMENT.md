# Patreon Token Management

This document describes the automatic Patreon OAuth2 token management system.

## Overview

The Patreon integration uses machine-to-machine (M2M) OAuth2 authentication with automatic token refresh. Tokens are stored in the `secrets.json` configuration file and automatically refreshed when they expire within 5 minutes.

## Configuration

### secrets.json Structure

Add the following keys to your `secrets.json` file (typically located at `/data/database/secrets.json` in production or `database/secrets.json` in development):

```json
{
  "patreon_client_id": "your_patreon_client_id",
  "patreon_client_secrete": "your_patreon_client_secret",
  "patreon_access_token": "your_initial_access_token",
  "patreon_refresh_token": "your_refresh_token",
  "patreon_expires_at": "2026-02-14T12:13:46.508421+00:00"
}
```

### Field Descriptions

- **patreon_client_id**: Your Patreon OAuth2 client ID
- **patreon_client_secrete**: Your Patreon OAuth2 client secret (note: uses 'secrete' spelling)
- **patreon_access_token**: Current access token for API requests
- **patreon_refresh_token**: Refresh token used to obtain new access tokens
- **patreon_expires_at**: ISO 8601 timestamp when the access token expires (with timezone)

## Automatic Token Refresh

### How It Works

1. **On Service Initialization**: When `PatreonClient` is initialized, it checks if the token expires within 5 minutes
2. **Before API Calls**: Before making any Patreon API call, the client ensures the token is valid
3. **Scheduled Task**: A background task runs every hour to proactively refresh tokens
4. **Automatic Update**: When a token is refreshed, the new values are automatically saved to `secrets.json`

### Refresh Threshold

Tokens are refreshed when they expire within **5 minutes** to ensure:
- No API calls fail due to expired tokens
- Sufficient time for the refresh operation to complete
- Grace period for any clock skew between systems

### Token Refresh Process

1. Client detects token expiring soon
2. Makes POST request to `https://www.patreon.com/api/oauth2/token` with:
   - `grant_type`: "refresh_token"
   - `refresh_token`: Current refresh token
   - `client_id`: OAuth2 client ID
   - `client_secret`: OAuth2 client secret
3. Receives new access token and optionally a new refresh token
4. Updates `secrets.json` with new values
5. Updates `patreon_expires_at` based on `expires_in` from response

## Usage

### Basic Usage

```python
from app.services.patreon_client import get_patreon_client, is_patreon_configured

# Check if Patreon is configured
if is_patreon_configured():
    # Get the client (automatically refreshes token if needed)
    client = get_patreon_client()
    
    # Fetch campaign members
    members = client.get_campaign_members("campaign_id")
    
    # Get specific member info
    member_info = client.get_member_info("member_id")
```

### Error Handling

```python
from app.services.patreon_client import PatreonTokenExpiredError

try:
    client = get_patreon_client()
    members = client.get_campaign_members("campaign_id")
except PatreonTokenExpiredError as e:
    # Token refresh failed
    logger.error(f"Patreon token refresh failed: {e}")
except requests.RequestException as e:
    # API request failed
    logger.error(f"Patreon API request failed: {e}")
```

### Scheduled Task

The token refresh task is automatically registered and runs every hour:

```python
# In app/extensions.py - automatically registered
scheduler.add_job(
    id="refresh_patreon_token",
    func=lambda: refresh_patreon_token(app),
    trigger="interval",
    hours=1,
    replace_existing=True,
)
```

## API Methods

### PatreonClient

#### `get_campaign_members(campaign_id: str) -> list[dict]`

Fetch all members (patrons) of a campaign.

**Parameters:**
- `campaign_id`: The Patreon campaign ID

**Returns:**
- List of member data dictionaries

**Example:**
```python
members = client.get_campaign_members("12345")
for member in members:
    print(f"Member: {member['attributes']['full_name']}")
```

#### `get_member_info(member_id: str) -> dict`

Get detailed information about a specific campaign member.

**Parameters:**
- `member_id`: The Patreon member ID

**Returns:**
- Member data dictionary

**Example:**
```python
member = client.get_member_info("67890")
print(f"Member status: {member['data']['attributes']['patron_status']}")
```

#### `is_configured() -> bool`

Check if Patreon credentials are configured.

**Returns:**
- `True` if all required credentials are present

## Security Considerations

### Token Storage

- Tokens are stored in `secrets.json` with restricted file permissions (0600)
- The file should only be readable by the application user
- Never commit `secrets.json` to version control

### Token Rotation

- Access tokens are automatically refreshed before expiry
- Refresh tokens may be rotated during the refresh process
- Old tokens are immediately replaced in the configuration

### API Security

- All API requests use Bearer token authentication
- Tokens are only sent over HTTPS
- Failed refresh attempts are logged but don't expose token values

## Troubleshooting

### Token Refresh Failures

If token refresh fails:

1. Check logs for error messages
2. Verify `patreon_client_id` and `patreon_client_secrete` are correct
3. Ensure `patreon_refresh_token` is still valid
4. Check network connectivity to `patreon.com`
5. Verify the Patreon OAuth2 application is still active

### Configuration Issues

If Patreon integration isn't working:

1. Verify all required fields are present in `secrets.json`
2. Check `patreon_expires_at` format is ISO 8601 with timezone
3. Ensure file has proper read/write permissions
4. Check application logs for configuration errors

### Manual Token Reset

If you need to manually update tokens:

1. Stop the application
2. Edit `secrets.json` with new token values
3. Update `patreon_expires_at` to a future timestamp
4. Restart the application

## Integration with User Model

The Patreon client integrates with the User model's Patreon fields:

```python
# User model fields (from previous PR)
user.patreon_id = "patreon_user_id"
user.is_patreon_supporter = True
user.patreon_tier = "premium"
```

To sync Patreon supporter status:

```python
from app.services.patreon_client import get_patreon_client
from app.models import User
from app.extensions import db

client = get_patreon_client()
members = client.get_campaign_members("campaign_id")

for member in members:
    # Find user by Patreon ID
    patreon_user_id = member['relationships']['user']['data']['id']
    user = User.query.filter_by(patreon_id=patreon_user_id).first()
    
    if user:
        # Update supporter status
        user.is_patreon_supporter = True
        # Extract tier from member data
        # ... tier logic ...
        db.session.commit()
```

## Development

### Testing

Run the test suite:

```bash
pytest tests/test_patreon_client.py -v
```

### Mock Configuration

For testing without real Patreon credentials:

```python
from unittest.mock import patch

with patch("app.services.patreon_client.load_secrets") as mock_load:
    mock_load.return_value = {
        "patreon_client_id": "test_id",
        "patreon_client_secrete": "test_secret",
        "patreon_access_token": "test_token",
        "patreon_refresh_token": "test_refresh",
        "patreon_expires_at": "2026-12-31T23:59:59+00:00"
    }
    # ... test code ...
```

## References

- [Patreon API Documentation](https://docs.patreon.com/)
- [OAuth2 Token Refresh](https://docs.patreon.com/#oauth)
- [Patreon API v2](https://docs.patreon.com/#apiv2-oauth)
