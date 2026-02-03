# Example: Using Media Counts and Patreon Features

## Using Media Count Variables in Jinja Templates

The following Jinja variables are now available in wizard step templates:

### Direct Access in Templates
```jinja2
Welcome! Your server currently has:
- {{ total_movies }} movies
- {{ total_shows }} shows (same as {{ total_series }})
- {{ total_episodes }} episodes
```

### Using the Media Counts Widget
```markdown
{{ widget:media_counts }}
```

This will display a styled grid showing all media counts with color-coded cards.

## Conditional Display Based on Patreon Status

You can show/hide content based on whether a user is a Patreon supporter:

```jinja2
{% if is_patreon_supporter %}
<div class="patreon-only-content">
  <h3>Thank you for supporting us on Patreon!</h3>
  <p>Your tier: {{ patreon_tier or 'Supporter' }}</p>
  <p>You have access to exclusive features...</p>
</div>
{% else %}
<div class="become-patron">
  <h3>Become a Patreon Supporter</h3>
  <p>Support our project and unlock exclusive features!</p>
  {{ widget:button url="https://patreon.com/yourproject" text="Join on Patreon" }}
</div>
{% endif %}
```

## Example Complete Wizard Step

```markdown
# Welcome to Our Media Server

{{ widget:media_counts }}

## Library Overview

Your library contains:
- **{{ total_movies }}** movies ready to watch
- **{{ total_shows }}** TV series with **{{ total_episodes }}** episodes

{% if is_patreon_supporter %}
|||
### 🌟 Patreon Supporter Benefits

Thank you for your support! As a **{{ patreon_tier or 'Supporter' }}** tier member, you have access to:
- Priority support
- Early access to new features
- Custom server configurations
|||
{% endif %}

## Getting Started

{{ widget:recently_added_media limit=6 }}

{{ widget:button url="{{ settings.external_url }}" text="Open {{ settings.server_name }}" }}
```

## Database Configuration

To mark a user as a Patreon supporter (until OAuth is implemented):

```python
from app.models import User
from app.extensions import db

# Find user
user = User.query.filter_by(username="example_user").first()

# Mark as Patreon supporter
user.is_patreon_supporter = True
user.patreon_tier = "premium"  # or "basic", "supporter", etc.
user.patreon_id = "12345678"   # Patreon user ID

db.session.commit()
```

## Using WizardStep `requires` Field

You can use the `requires` field in the database to conditionally show steps:

```python
from app.models import WizardStep
from app.extensions import db

# Create a step that only shows for Patreon supporters
step = WizardStep(
    server_type="plex",
    category="post_invite",
    position=10,
    title="Patreon Exclusive Features",
    markdown="# Premium Features\n\nThank you for your support!",
    requires=["is_patreon_supporter"]  # This will be checked in future implementation
)
db.session.add(step)
db.session.commit()
```

Note: The `requires` field filtering based on Patreon status will need additional implementation in the wizard routing logic to check user attributes rather than just settings.
