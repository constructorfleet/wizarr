---
title: "{{ _('Library Statistics') }}"
---

## 📊 {{ _('Your Media Library') }}

{{ _('Welcome! Here\'s an overview of what\'s available in your media collection:') }}

{{ widget:media_counts }}

|||
### 🎬 {{ _('Media Breakdown') }}

{{ _('Our library currently contains:') }}
- **{{ total_movies }}** {{ _('movies ready to stream') }}
- **{{ total_shows }}** {{ _('TV series') }}
- **{{ total_episodes }}** {{ _('episodes available') }}

{{ _('The collection is constantly growing with new content added regularly!') }}
|||

## 🆕 {{ _('Recently Added') }}

{{ _('Check out what\'s been added to the library recently:') }}

{{ widget:recently_added_media limit=8 }}

{% if is_patreon_supporter %}
|||
### 🌟 {{ _('Thank You, Patreon Supporter!') }}

{{ _('As a') }} **{{ patreon_tier or _('Supporter') }}** {{ _('tier member, you have access to:') }}
- ⚡ {{ _('Priority streaming (reduced wait times)') }}
- 📺 {{ _('Early access to new content') }}
- 🎯 {{ _('Custom request queue') }}
- 🛠️ {{ _('Exclusive features and settings') }}

{{ _('Thank you for supporting our project! Your contribution helps keep the server running and the library growing.') }} 💚
|||
{% else %}
|||
### 💝 {{ _('Support Us on Patreon') }}

{{ _('Consider becoming a patron to help support the server and unlock exclusive benefits:') }}
- 🚀 {{ _('Priority streaming access') }}
- 🎬 {{ _('Early access to new releases') }}
- 🎯 {{ _('Content request priority') }}
- ⭐ {{ _('Exclusive features and customization') }}

{{ widget:button url="https://patreon.com/yourproject" text=_("Become a Patron") }}
|||
{% endif %}

## 🎮 {{ _('Ready to Start?') }}

{{ widget:button url="{{ settings.external_url }}" text=_("Open") + " " + settings.server_name }}
