#!/usr/bin/env python3
"""Seeds /data/config.json from Home Assistant options on first run."""
import json
import os

OPTIONS_FILE = "/data/options.json"
CONFIG_FILE = "/data/config.json"

if os.path.exists(OPTIONS_FILE) and not os.path.exists(CONFIG_FILE):
    with open(OPTIONS_FILE) as f:
        options = json.load(f)
    with open(CONFIG_FILE, "w") as f:
        json.dump(options, f, indent=2)
    print("Config seeded from HA options")
elif not os.path.exists(CONFIG_FILE):
    default = {
        "bring_email": "",
        "bring_password": "",
        "list_uuid": "",
        "list_name": "",
        "trmnl_webhook_url": "",
        "poll_interval_minutes": 5,
        "webhook_interval_minutes": 30,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(default, f, indent=2)
    print("Default config created")
