# Patreon Token Management - Implementation Summary

## Overview

This implementation provides automatic OAuth2 token management for Patreon API integration, ensuring seamless API access without manual token intervention.

## Problem Statement

The requirement was to:
> "Patreon client id, client secret, access token and refresh token will be provided via a config file. If `patreon_expires_at` will expire within 5 minutes, refresh the token via `api/oauth2/token` and update the config file with the new values. Treat Patreon api as machine to machine."

## Solution

A complete token management system that:
1. Stores credentials in `secrets.json`
2. Automatically refreshes tokens before expiry
3. Uses machine-to-machine OAuth2 flow
4. Updates configuration file with new tokens
5. Runs background refresh task
6. Provides clean API for Patreon operations

## Components Implemented

### 1. PatreonClient Service
**File**: `app/services/patreon_client.py`

**Features**:
- Loads credentials from `secrets.json` on initialization
- Checks token expiry before each operation
- Automatically refreshes tokens via OAuth2 API
- Saves updated tokens back to configuration
- Provides campaign member API methods
- Singleton pattern for efficiency
- Comprehensive error handling

**Key Methods**:
```python
class PatreonClient:
    def _ensure_token_valid()         # Check and refresh if needed
    def _is_token_expiring_soon()     # Check if expires within 5 minutes
    def _refresh_access_token()       # Refresh via OAuth2 API
    def get_campaign_members()        # Fetch patron list
    def get_member_info()             # Get patron details
```

### 2. Scheduled Refresh Task
**File**: `app/tasks/patreon_refresh.py`

**Features**:
- Runs every hour via APScheduler
- Proactively checks token status
- Triggers refresh if expiring soon
- Logs all operations
- Handles errors gracefully

**Registration**: Automatically registered in `app/extensions.py`

### 3. Configuration Format
**Location**: `database/secrets.json` (or `/data/database/secrets.json` in production)

**Structure**:
```json
{
  "patreon_client_id": "your_client_id",
  "patreon_client_secrete": "your_client_secret",
  "patreon_access_token": "current_access_token",
  "patreon_refresh_token": "refresh_token",
  "patreon_expires_at": "2026-02-14T12:13:46.508421+00:00"
}
```

**Note**: Field uses `patreon_client_secrete` spelling as per requirement specification.

### 4. Comprehensive Tests
**File**: `tests/test_patreon_client.py`

**Coverage**:
- Token loading and saving (3 tests)
- Expiry detection (5 tests)
- Refresh logic (6 tests)
- API calls (2 tests)
- Error handling (4 tests)
- Helper functions (2 tests)
- Edge cases (2 tests)

**Total**: 24 test cases with mocking for external dependencies

### 5. Documentation
**File**: `PATREON_TOKEN_MANAGEMENT.md`

**Contents**:
- Configuration setup
- Automatic refresh behavior
- API reference
- Security considerations
- Troubleshooting guide
- Integration examples
- Development notes

### 6. Example Script
**File**: `examples/patreon_example.py`

**Features**:
- Interactive demonstration
- Configuration setup
- Token status check
- Refresh demonstration
- API call examples

## Token Refresh Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PatreonClient.get_patreon_client()                       │
│    - Loads credentials from secrets.json                    │
│    - Calls _ensure_token_valid()                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Check if token expires within 5 minutes                  │
│    - Compare expires_at with current time + 5 minutes       │
│    - Handle timezone-aware datetime                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ (expires soon)
┌─────────────────────────────────────────────────────────────┐
│ 3. POST https://www.patreon.com/api/oauth2/token           │
│    Request Body:                                             │
│    {                                                         │
│      "grant_type": "refresh_token",                         │
│      "refresh_token": "<current_refresh_token>",            │
│      "client_id": "<client_id>",                            │
│      "client_secret": "<client_secret>"                     │
│    }                                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Receive Response:                                         │
│    {                                                         │
│      "access_token": "<new_access_token>",                  │
│      "refresh_token": "<new_refresh_token>",  (optional)    │
│      "expires_in": 2592000  (30 days)                       │
│    }                                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Update secrets.json:                                      │
│    - Set patreon_access_token = new_access_token           │
│    - Set patreon_refresh_token = new_refresh_token         │
│    - Set patreon_expires_at = now + expires_in seconds     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Continue with API operations using new token             │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Basic Usage

```python
from app.services.patreon_client import get_patreon_client

# Get client (automatically handles token refresh)
client = get_patreon_client()

# Fetch campaign members
members = client.get_campaign_members("12345")

# Get member details
member = client.get_member_info("67890")
```

### Check Configuration

```python
from app.services.patreon_client import is_patreon_configured

if is_patreon_configured():
    print("Patreon is ready to use")
else:
    print("Please configure Patreon credentials")
```

### Error Handling

```python
from app.services.patreon_client import PatreonTokenExpiredError

try:
    client = get_patreon_client()
    members = client.get_campaign_members("12345")
except PatreonTokenExpiredError as e:
    logger.error(f"Token refresh failed: {e}")
except Exception as e:
    logger.error(f"Patreon API error: {e}")
```

## Security Features

### Token Storage
- Stored in `secrets.json` with 0600 permissions
- File location in secure database directory
- Never committed to version control
- No tokens in logs or error messages

### Token Rotation
- Automatic refresh before expiry
- Old tokens immediately replaced
- Refresh tokens may rotate during refresh
- No manual intervention required

### API Security
- HTTPS-only communication
- Bearer token authentication
- Request timeout protection (30 seconds)
- Proper error handling

## Performance

### Efficiency Optimizations
- Singleton pattern (single client instance)
- Token checked only when needed
- Scheduled refresh reduces on-demand checks
- Minimal configuration file I/O

### Refresh Timing
- **5-minute threshold**: Ensures ample time for refresh
- **Hourly scheduled task**: Proactive refresh
- **On-demand refresh**: When token expires soon
- **Graceful degradation**: Service continues if refresh fails temporarily

## Testing

### Test Coverage
```
Test Statistics:
- Total Tests: 24
- Test Classes: 2
- Mock Usage: Extensive (requests, file I/O)
- Edge Cases: Covered
- Error Scenarios: Tested
```

### Running Tests
```bash
pytest tests/test_patreon_client.py -v
```

## Deployment

### Setup Steps

1. **Add Credentials to secrets.json**:
   ```bash
   cd /data/database  # or database/ in dev
   vi secrets.json
   ```

2. **Add Patreon Configuration**:
   ```json
   {
     "patreon_client_id": "...",
     "patreon_client_secrete": "...",
     "patreon_access_token": "...",
     "patreon_refresh_token": "...",
     "patreon_expires_at": "2026-02-14T12:13:46.508421+00:00"
   }
   ```

3. **Restart Application**:
   ```bash
   docker-compose restart
   # or
   systemctl restart wizarr
   ```

4. **Verify Operation**:
   - Check logs for "Patreon token refresh check"
   - Run example script: `python examples/patreon_example.py`

### Monitoring

**Log Messages**:
- `"Patreon token expiring soon, refreshing..."` - Refresh triggered
- `"Patreon access token refreshed successfully"` - Success
- `"Failed to refresh Patreon token: ..."` - Error

**Scheduled Task**:
- Runs every hour
- Check scheduler logs for execution
- Task ID: `refresh_patreon_token`

## Troubleshooting

### Token Refresh Fails
1. Verify credentials in `secrets.json`
2. Check refresh token is still valid
3. Ensure network connectivity to patreon.com
4. Review application logs for errors

### Configuration Not Loading
1. Check file permissions on `secrets.json`
2. Verify JSON syntax is valid
3. Ensure datetime format is ISO 8601
4. Check file location matches application config

### API Calls Fail
1. Verify token was refreshed successfully
2. Check campaign_id is correct
3. Ensure OAuth application is active
4. Review Patreon API documentation

## Future Enhancements

Possible improvements:
- OAuth flow for initial token acquisition
- Admin UI for credential management
- Automatic patron sync with User model
- Webhook support for real-time updates
- Rate limiting and retry logic
- Token refresh metrics/monitoring

## Files Modified

| File | Lines | Description |
|------|-------|-------------|
| `app/services/patreon_client.py` | 301 | Core client implementation |
| `app/tasks/patreon_refresh.py` | 65 | Scheduled refresh task |
| `app/extensions.py` | 9 | Task registration |
| `tests/test_patreon_client.py` | 386 | Comprehensive tests |
| `PATREON_TOKEN_MANAGEMENT.md` | 356 | User documentation |
| `examples/patreon_example.py` | 133 | Example script |

**Total**: 6 files created/modified, ~1250 lines of code

## Quality Assurance

✅ **Python Syntax**: All files validated  
✅ **Code Review**: Completed  
✅ **Security Scan**: CodeQL - No issues  
✅ **Test Coverage**: 24 test cases  
✅ **Documentation**: Complete  
✅ **Example Code**: Provided  

## Conclusion

This implementation provides a robust, production-ready solution for Patreon OAuth2 token management. The system automatically handles token refresh with zero manual intervention required, ensuring continuous API access for Patreon integration features.

The code follows best practices for security, error handling, and maintainability, and includes comprehensive documentation and testing to support long-term maintenance.
