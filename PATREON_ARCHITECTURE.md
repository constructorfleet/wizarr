# Patreon Token Management Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Wizarr Application                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐         ┌─────────────────────────────┐     │
│  │  Application     │         │   APScheduler (Hourly)      │     │
│  │  Startup         │         │                             │     │
│  │                  │         │  refresh_patreon_token()    │     │
│  │  • Load config   │         │                             │     │
│  │  • Init services │         │  ┌─────────────────────┐    │     │
│  │  • Start tasks   │◄────────┤  │ Check token expiry  │    │     │
│  └────────┬─────────┘         │  │ Refresh if needed   │    │     │
│           │                   │  └─────────────────────┘    │     │
│           ▼                   └──────────────┬──────────────┘     │
│  ┌──────────────────┐                       │                    │
│  │  PatreonClient   │◄──────────────────────┘                    │
│  │  (Singleton)     │                                             │
│  │                  │                                             │
│  │  • Load config   │         ┌─────────────────────────────┐    │
│  │  • Check expiry  │         │   API Operations            │    │
│  │  • Auto refresh  │◄────────┤                             │    │
│  │  • Save config   │         │  • get_campaign_members()   │    │
│  └────────┬─────────┘         │  • get_member_info()        │    │
│           │                   └─────────────────────────────┘    │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              secrets.json                            │        │
│  │  {                                                   │        │
│  │    "patreon_client_id": "...",                       │        │
│  │    "patreon_client_secrete": "...",                  │        │
│  │    "patreon_access_token": "...",                    │        │
│  │    "patreon_refresh_token": "...",                   │        │
│  │    "patreon_expires_at": "2026-02-14T12:13:46+00:00" │        │
│  │  }                                                   │        │
│  └────────┬─────────────────────────────────────────────┘        │
│           │                                                       │
└───────────┼───────────────────────────────────────────────────────┘
            │
            │ HTTPS POST (Token Refresh)
            │
            ▼
┌───────────────────────────────────────────────────────────┐
│         Patreon OAuth2 API                                │
│                                                           │
│  POST /api/oauth2/token                                   │
│  {                                                        │
│    "grant_type": "refresh_token",                        │
│    "refresh_token": "...",                               │
│    "client_id": "...",                                   │
│    "client_secret": "..."                                │
│  }                                                        │
│                                                           │
│  Response:                                                │
│  {                                                        │
│    "access_token": "new_token",                          │
│    "refresh_token": "new_refresh",                       │
│    "expires_in": 2592000                                 │
│  }                                                        │
└───────────────────────────────────────────────────────────┘
```

## Token Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ Token State Machine                                         │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   Token      │
    │   Created    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   Token      │───────────────────┐
    │   Valid      │                   │
    │ (> 5 min)    │                   │
    └──────┬───────┘                   │
           │                           │
           │ Time passes               │ API Call
           │                           │
           ▼                           ▼
    ┌──────────────┐            ┌──────────────┐
    │   Token      │            │   Normal     │
    │  Expiring    │            │   Operation  │
    │ (< 5 min)    │            └──────────────┘
    └──────┬───────┘
           │
           │ Automatic
           │ Refresh
           ▼
    ┌──────────────┐
    │  Refreshing  │
    │   Token      │
    └──────┬───────┘
           │
           │ Success
           ▼
    ┌──────────────┐
    │   Token      │
    │  Updated     │
    │ (secrets.json)│
    └──────┬───────┘
           │
           └───────────────┐
                           │
                           ▼
                    ┌──────────────┐
                    │   Token      │
                    │   Valid      │
                    │ (> 5 min)    │
                    └──────────────┘
```

## Component Interaction

```
┌────────────────────────────────────────────────────────────────┐
│ Request Flow: Fetch Campaign Members                           │
└────────────────────────────────────────────────────────────────┘

Application Code
    │
    │ get_patreon_client()
    ▼
┌────────────────────────────────────────┐
│ PatreonClient.__init__()               │
│                                        │
│ 1. Load config from secrets.json      │
│ 2. Parse patreon_expires_at           │
│ 3. Call _ensure_token_valid()         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ _is_token_expiring_soon()              │
│                                        │
│ • now = current_time                   │
│ • threshold = now + 5 minutes          │
│ • return expires_at < threshold        │
└────────┬───────────────────────────────┘
         │
         ├── False (token valid) ────────────┐
         │                                   │
         └── True (token expiring)           │
                   │                         │
                   ▼                         │
         ┌────────────────────────┐         │
         │ _refresh_access_token()│         │
         │                        │         │
         │ POST to Patreon API    │         │
         │ Update tokens          │         │
         │ Save to secrets.json   │         │
         └────────┬───────────────┘         │
                  │                         │
                  └─────────────────────────┘
                                            │
Application Code                            │
    │                                       │
    │ get_campaign_members(campaign_id)◄───┘
    ▼
┌────────────────────────────────────────┐
│ _ensure_token_valid()                  │
│ (called again before API call)         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ API Call to Patreon                    │
│                                        │
│ GET /api/oauth2/v2/campaigns/{id}      │
│ Authorization: Bearer {access_token}   │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Return campaign members                │
└────────────────────────────────────────┘
```

## Scheduled Task Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Hourly Scheduled Task                                          │
└────────────────────────────────────────────────────────────────┘

APScheduler (Every hour)
    │
    │ trigger: interval, hours=1
    ▼
┌────────────────────────────────────────┐
│ refresh_patreon_token(app)             │
│                                        │
│ 1. Check is_patreon_configured()       │
└────────┬───────────────────────────────┘
         │
         ├── False (not configured) ────> Log: "Patreon not configured"
         │                                Exit
         │
         └── True (configured)
                   │
                   ▼
         ┌────────────────────────┐
         │ get_patreon_client()   │
         └────────┬───────────────┘
                  │
                  │ (automatically checks token)
                  │
                  ▼
         ┌────────────────────────┐
         │ Token Status Check     │
         │                        │
         │ • If expiring soon:    │
         │   - Refresh triggered  │
         │   - Tokens updated     │
         │   - Log success        │
         │                        │
         │ • If still valid:      │
         │   - No action needed   │
         │   - Log "still valid"  │
         └────────────────────────┘
```

## Error Handling Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Error Scenarios                                                │
└────────────────────────────────────────────────────────────────┘

Token Refresh Attempt
    │
    ▼
┌────────────────────────────────────────┐
│ POST /api/oauth2/token                 │
└────────┬───────────────────────────────┘
         │
         ├── Success ──────────────────────────> Update tokens
         │                                       Continue operation
         │
         ├── Network Error ─────────┐
         │                          │
         ├── Invalid Credentials ───┤
         │                          │
         ├── Expired Refresh Token ─┤
         │                          │
         └── Server Error ──────────┤
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │ Raise Exception:    │
                          │ PatreonTokenExpired │
                          │ Error               │
                          └─────────┬───────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │ Caller Handles:     │
                          │                     │
                          │ • Log error         │
                          │ • Retry later       │
                          │ • Alert admin       │
                          │ • Degrade gracefully│
                          └─────────────────────┘
```

## Configuration Management

```
┌────────────────────────────────────────────────────────────────┐
│ secrets.json Lifecycle                                         │
└────────────────────────────────────────────────────────────────┘

Initial Setup (Manual)
    │
    │ Admin adds credentials
    ▼
┌────────────────────────────────────────┐
│ secrets.json                           │
│ {                                      │
│   "patreon_client_id": "...",          │
│   "patreon_client_secrete": "...",     │
│   "patreon_access_token": "...",       │
│   "patreon_refresh_token": "...",      │
│   "patreon_expires_at": "..."          │
│ }                                      │
└────────┬───────────────────────────────┘
         │
         │ Application reads
         ▼
┌────────────────────────────────────────┐
│ PatreonClient loads config             │
└────────┬───────────────────────────────┘
         │
         │ Token refresh occurs
         ▼
┌────────────────────────────────────────┐
│ PatreonClient saves updated config     │
│                                        │
│ • New access_token                     │
│ • New refresh_token (if provided)      │
│ • New expires_at (now + expires_in)    │
└────────┬───────────────────────────────┘
         │
         │ save_secrets()
         ▼
┌────────────────────────────────────────┐
│ secrets.json (updated)                 │
│ {                                      │
│   "patreon_client_id": "...",          │
│   "patreon_client_secrete": "...",     │
│   "patreon_access_token": "NEW",       │
│   "patreon_refresh_token": "NEW",      │
│   "patreon_expires_at": "NEW"          │
│ }                                      │
└────────────────────────────────────────┘
```

## Security Layers

```
┌────────────────────────────────────────────────────────────────┐
│ Security Architecture                                          │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐
│ Application Layer               │
│                                 │
│ • No tokens in logs             │
│ • No tokens in error messages   │
│ • Tokens in memory only         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ File System Layer               │
│                                 │
│ • secrets.json                  │
│   - Permissions: 0600           │
│   - Owner: app user only        │
│   - Location: secure directory  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Network Layer                   │
│                                 │
│ • HTTPS only                    │
│ • TLS 1.2+ required             │
│ • Certificate validation        │
│ • Timeout: 30 seconds           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Patreon API                     │
│                                 │
│ • OAuth2 validation             │
│ • Rate limiting                 │
│ • Token expiration              │
└─────────────────────────────────┘
```

## Deployment Architecture

```
Production Environment

┌───────────────────────────────────────────────────────────┐
│ Container / Server                                        │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Wizarr Application                                  │ │
│  │                                                     │ │
│  │  • Flask application                                │ │
│  │  • APScheduler (background tasks)                   │ │
│  │  • PatreonClient (singleton)                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ /data/database/                                     │ │
│  │                                                     │ │
│  │  • database.db                                      │ │
│  │  • secrets.json ◄── Patreon tokens here             │ │
│  │  • sessions/                                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                          │                                │
└──────────────────────────┼────────────────────────────────┘
                           │
                           │ Persistent Volume Mount
                           │
                    ┌──────▼───────┐
                    │   Host FS    │
                    │              │
                    │ /data/       │
                    └──────────────┘
```

---

## Key Design Decisions

### 1. Singleton Pattern
**Why**: Ensures single instance of PatreonClient across application
**Benefit**: Prevents duplicate refresh operations and maintains state

### 2. 5-Minute Threshold
**Why**: Provides buffer time for refresh operation
**Benefit**: Prevents token expiry during API calls

### 3. Automatic Refresh on Init
**Why**: Ensures token is valid before any operations
**Benefit**: Eliminates race conditions and API failures

### 4. Hourly Scheduled Task
**Why**: Proactive token maintenance
**Benefit**: Reduces on-demand refresh operations

### 5. secrets.json Storage
**Why**: Leverages existing configuration system
**Benefit**: Consistent with application architecture

### 6. Timezone-Aware Datetimes
**Why**: Handles various server timezones
**Benefit**: Accurate expiry calculations globally

---

**Last Updated**: 2026-02-04  
**Version**: 1.0  
**Author**: Wizarr Development Team
