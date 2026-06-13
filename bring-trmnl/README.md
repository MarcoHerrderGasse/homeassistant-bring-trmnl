# Bring! → TRMNL · Home Assistant Add-on

[![Version](https://img.shields.io/badge/version-1.4.3-blue.svg)](CHANGELOG.md)
[![HA Ingress](https://img.shields.io/badge/HA-Ingress-brightgreen.svg)](https://www.home-assistant.io/integrations/hassio/#ingress)
[![Supports aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)]()
[![Supports amd64](https://img.shields.io/badge/amd64-yes-green.svg)]()
[![Supports armv7](https://img.shields.io/badge/armv7-yes-green.svg)]()

Polls your [Bring!](https://www.getbring.com/) shopping list and pushes it to a [TRMNL](https://usetrmnl.com/) e-ink display — with product icons, section grouping, and a fully mobile-optimised web UI directly in Home Assistant.

---

## Features

- **Automatic sync** — polls Bring! at a configurable interval and pushes only when the list changes (MD5-based change detection)
- **Product icons** — each item is shown with its official Bring! product icon on the TRMNL display
- **Section grouping** — items are mapped to their Bring! store sections/categories
- **Multiple TRMNL devices** — supports multiple webhook URLs for parallel push to several displays
- **Web UI via HA Ingress** — configure and monitor directly from the HA sidebar, no separate port needed
- **Mobile-optimised** — fully usable from the HA mobile app, collapsible sidebar
- **No YAML config** — everything is set up through the built-in wizard and settings page

---

## Requirements

| Requirement | Details |
|---|---|
| [Bring!](https://www.getbring.com/) account | Free account with at least one shopping list |
| [TRMNL](https://usetrmnl.com/) device | A Custom Plugin webhook URL from the TRMNL dashboard |
| Home Assistant | Any recent version with Supervisor (HA OS or Supervised) |

---

## Installation

### Via Custom Repository (recommended)

1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories** and add this repository URL
3. Find **Bring! → TRMNL** in the store and click **Install**
4. Start the add-on and open the **Web UI** to run the setup wizard

### Via Local Add-on (SMB / development)

1. Copy the `bring-trmnl` folder to the `/addons/` directory on your HA instance
2. In HA: **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**
3. The add-on appears under **Local add-ons** — install and start it

---

## Setup Wizard

On first start the add-on opens a 4-step wizard:

1. **Bring! login** — enter your email and password; the add-on fetches your lists
2. **List selection** — choose which list to display on TRMNL
3. **TRMNL Webhook** — paste the webhook URL from your TRMNL Custom Plugin
4. **Intervals** — set how often to poll Bring! and the maximum push gap

---

## Configuration

All settings are managed in the **Settings** tab of the web UI.

| Field | Description | Default |
|---|---|---|
| Bring! E-Mail | Bring! account email | — |
| Bring! Password | Bring! account password | — |
| Shopping list | Bring! list to sync | — |
| TRMNL Webhook URL | One or more webhook URLs (one per row) | — |
| Poll interval | How often to check Bring! for changes (minutes) | `5` |
| Forced push interval | Maximum gap between pushes even without changes (minutes) | `30` |

---

## TRMNL Liquid Template

The add-on sends these merge variables to your TRMNL Custom Plugin:

```json
{
  "merge_variables": {
    "ln": "List name",
    "au": "username",
    "ib": "https://web.getbring.com/assets/images/items/",
    "col": [
      { "it": "Äpfel", "ic": "aepfel.png" },
      { "it": "Milch", "ic": "milch.png" }
    ]
  }
}
```

Use `{{ ib }}{{ item.ic }}` in your Liquid template to render product icons.

---

## How it works

```
Bring! API ──poll──▶ MD5 changed? ──yes──▶ fetch icons ──▶ push to TRMNL webhook(s)
                          │
                    interval elapsed?
                          │
                         yes──────────────────────────────▶ push to TRMNL webhook(s)
```

Two processes run in parallel inside the add-on container:

- **Daemon** (`main.py`) — the poll loop, persists state in `/data/.state`
- **Web UI** (`web.py`) — Flask + Waitress served via HA Ingress on port 8099

---

## Changelog

The full version history is available in the **Changelog** tab in the Home Assistant add-on UI.
