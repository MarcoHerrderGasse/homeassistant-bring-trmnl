# Bring! → TRMNL

Polls your [Bring!](https://www.getbring.com/) shopping list at a configurable interval and pushes it to a [TRMNL](https://usetrmnl.com/) e-ink display. Each item is shown with its product icon, loaded from the official Bring! asset CDN.

## Prerequisites

- An active [Bring!](https://www.getbring.com/) account with at least one shopping list
- A [TRMNL](https://usetrmnl.com/) device with a **Custom Plugin** webhook URL
  - In the TRMNL dashboard go to **Plugins → Custom Plugin → Create** and copy the webhook URL

## Installation

1. In Home Assistant open **Settings → Add-ons → Add-on Store**
2. Click the three-dot menu (⋮) in the top-right corner and choose **Repositories**
3. Add this repository URL and click **Add**
4. Find **Bring! → TRMNL** in the store and click **Install**
5. After installation, open the add-on and click **Open Web UI**
6. The setup wizard guides you through the following steps:
   - Sign in with your Bring! account
   - Select the shopping list to display
   - Enter your TRMNL webhook URL
   - Configure sync intervals

## Configuration

All settings are managed through the built-in web UI (no YAML configuration required).

| Setting | Description | Default |
|---|---|---|
| **Bring! E-Mail** | Your Bring! account email address | — |
| **Bring! Password** | Your Bring! account password | — |
| **Shopping list** | The Bring! list to display on TRMNL | — |
| **TRMNL Webhook URL** | Webhook URL from the TRMNL Custom Plugin dashboard | — |
| **Poll interval (minutes)** | How often the add-on checks Bring! for changes | `5` |
| **Forced push interval (minutes)** | Maximum gap between pushes, even without list changes | `30` |

Multiple TRMNL webhook URLs are supported — add one per device in the settings.

## TRMNL Template

The add-on sends the following merge variables to TRMNL:

| Variable | Content |
|---|---|
| `ln` | List name |
| `au` | Username (email prefix) |
| `ib` | Bring! icon base URL |
| `col` | Array of `{ it: "Item name", ic: "icon.png" }` objects |

Use `{{ ib }}{{ item.ic }}` in your Liquid template to render product icons.

## How it works

The add-on runs two processes in parallel:

1. **Daemon** — polls Bring! every `poll_interval_minutes`. If the list has changed (detected via MD5 hash) **or** `webhook_interval_minutes` have passed since the last push, it sends the updated list to TRMNL.
2. **Web UI** — a small Flask/Gunicorn web server that serves the configuration and status dashboard via Home Assistant Ingress.

State (last hash + last push timestamp) is persisted in `/data/.state` so the daemon survives restarts without unnecessary pushes.

## Troubleshooting

**List not updating on TRMNL**
Check the **Logs** tab in the web UI. Common causes: wrong webhook URL, TRMNL rate limiting, or Bring! API errors.

**"Login fehlgeschlagen"**
Verify your Bring! credentials in the **Settings** tab. The email field intentionally has autocomplete disabled to prevent stale credentials being filled in automatically.

**Add-on crashes on start**
Check the Home Assistant **Supervisor → Logs** for startup errors. Ensure the `/data` volume is writable.
