import json
import os

DATA_DIR = "/data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


def read_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    raw_urls = data.get("trmnl_webhook_url", "")
    webhook_urls = [u.strip() for u in raw_urls.split(",") if u.strip()]
    return {
        "email": data.get("bring_email", ""),
        "password": data.get("bring_password", ""),
        "list_uuid": data.get("list_uuid", ""),
        "list_name": data.get("list_name", ""),
        "webhook_url": webhook_urls[0] if webhook_urls else "",
        "webhook_urls": webhook_urls,
        "poll_interval": int(data.get("poll_interval_minutes", 5)),
        "webhook_interval": int(data.get("webhook_interval_minutes", 30)),
    }


def read_raw_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "bring_email": "",
            "bring_password": "",
            "list_uuid": "",
            "list_name": "",
            "trmnl_webhook_url": "",
            "poll_interval_minutes": 5,
            "webhook_interval_minutes": 30,
        }


def write_raw_config(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
