# Patreon OAuth2 Token Management - Quick Start

## Overview

Automatic token refresh system for Patreon API integration. Tokens are refreshed when they expire within 5 minutes.

## Setup

### 1. Add Configuration

Edit `/data/database/secrets.json` (or `database/secrets.json` in dev):

```json
{
  "patreon_client_id": "your_client_id",
  "patreon_client_secrete": "your_client_secret",
  "patreon_access_token": "your_initial_token",
  "patreon_refresh_token": "your_refresh_token",
  "patreon_expires_at": "2026-02-14T12:13:46.508421+00:00"
}
```

### 2. Restart Application

```bash
docker-compose restart
# or
systemctl restart wizarr
```

### 3. Verify

```bash
# Check logs for token refresh
docker-compose logs -f | grep -i patreon

# Or run example script
python examples/patreon_example.py
```

## Usage

```python
from app.services.patreon_client import get_patreon_client

# Automatically refreshes token if needed
client = get_patreon_client()

# Fetch campaign members
members = client.get_campaign_members("campaign_id")

# Get member details
member = client.get_member_info("member_id")
```

## How It Works

1. **Automatic Check**: Token expiry checked on client initialization
2. **5-Minute Threshold**: Refresh triggered if expires within 5 minutes
3. **OAuth2 Refresh**: POST to `https://www.patreon.com/api/oauth2/token`
4. **Config Update**: New tokens saved to `secrets.json`
5. **Scheduled Task**: Hourly background task for proactive refresh

## Files

- `app/services/patreon_client.py` - Main client implementation
- `app/tasks/patreon_refresh.py` - Scheduled refresh task
- `tests/test_patreon_client.py` - Comprehensive test suite
- `examples/patreon_example.py` - Interactive demo script

## Documentation

- **User Guide**: `PATREON_TOKEN_MANAGEMENT.md` - Configuration and usage
- **Technical Details**: `PATREON_IMPLEMENTATION_SUMMARY.md` - Architecture and flow
- **Diagrams**: `PATREON_ARCHITECTURE.md` - Visual system overview

## Troubleshooting

### Token Refresh Fails

1. Verify credentials in `secrets.json`
2. Check `patreon_refresh_token` is valid
3. Ensure network connectivity to patreon.com
4. Review logs: `docker-compose logs | grep -i patreon`

### Configuration Not Loading

1. Check file permissions: `chmod 600 secrets.json`
2. Verify JSON syntax
3. Ensure datetime format is ISO 8601 with timezone
4. Check file location matches application config

## Monitoring

### Log Messages

- `Patreon token expiring soon, refreshing...` - Refresh triggered
- `Patreon access token refreshed successfully` - Success
- `Failed to refresh Patreon token: ...` - Error

### Scheduled Task

- Task ID: `refresh_patreon_token`
- Interval: Every hour
- Check APScheduler logs for execution

## Security

- ✅ Tokens stored in `secrets.json` (0600 permissions)
- ✅ HTTPS-only communication
- ✅ No tokens in logs or errors
- ✅ Automatic token rotation
- ✅ File location in secure database directory

## Testing

```bash
# Run test suite
pytest tests/test_patreon_client.py -v

# Run example script
python examples/patreon_example.py

# Check configuration
python examples/patreon_example.py --setup
```

## Support

- Check documentation files for detailed information
- Review test cases for usage examples
- Run example script for interactive testing

---

**Version**: 1.0  
**Last Updated**: 2026-02-04  
**Status**: Production Ready ✅
