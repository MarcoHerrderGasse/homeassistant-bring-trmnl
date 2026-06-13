#!/usr/bin/env python3
import gc
import hashlib
import json
import logging
import os
import sys
import time
import requests
from config_manager import read_config
from bring_api import (
    authenticate, fetch_shopping_list, fetch_list_details,
    load_translations, load_catalog_sections, resolve_icon, ICON_BASE_URL,
)

DATA_DIR = "/data"
STATE_FILE = os.path.join(DATA_DIR, ".state")
STATUS_FILE = os.path.join(DATA_DIR, ".status")
ITEMS_FILE = os.path.join(DATA_DIR, ".last_items")
LOG_FILE = os.path.join(DATA_DIR, "bring_trmnl.log")
TRIGGER_FILE = os.path.join(DATA_DIR, ".sync_trigger")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger(__name__)

SECTION_ORDER = [
    "Obst & Gemüse", "Brot & Gebäck", "Milch & Käse", "Fleisch & Fisch",
    "Zutaten & Gewürze", "Fertig- & Tiefkühlprodukte", "Getreideprodukte",
    "Snacks & Süsswaren", "Getränke", "Haushalt", "Pflege & Gesundheit",
    "Tierbedarf", "Baumarkt & Garten", "Eigene Artikel",
]


def _fix_encoding(s: str) -> str:
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def _section_rank(section: str) -> int:
    fixed = _fix_encoding(section)
    try:
        return SECTION_ORDER.index(fixed)
    except ValueError:
        return len(SECTION_ORDER)


def _list_hash(items: list) -> str:
    return hashlib.md5(
        json.dumps(sorted(items, key=lambda x: x.get("name", "")), ensure_ascii=False).encode()
    ).hexdigest()


def _read_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_hash": "", "last_push_ts": 0}


def _write_state(list_hash: str):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_hash": list_hash, "last_push_ts": time.time()}, f)


def _write_status(status: dict):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f)
    except Exception:
        pass


def _write_items(items: list):
    try:
        with open(ITEMS_FILE, "w") as f:
            json.dump(items, f)
    except Exception:
        pass


def push_to_trmnl(items: list, translations: dict, details_map: dict, cfg: dict) -> bool:
    col = []
    for item in items:
        original = item["name"]
        display = translations.get(original, original)
        icon_name = details_map.get(original, original)
        col.append({"it": display, "ic": resolve_icon(icon_name)})

    payload = {
        "merge_variables": {
            "ln": cfg["list_name"] or "Einkaufsliste",
            "au": cfg["email"].split("@")[0],
            "ib": ICON_BASE_URL,
            "col": col,
        }
    }

    success = False
    for url in cfg["webhook_urls"]:
        try:
            response = requests.post(url, json=payload,
                                     headers={"Content-Type": "application/json"}, timeout=15)
            if response.status_code in (200, 201, 202):
                log.info(f"[OK] {len(col)} Artikel gesendet → {url}")
                success = True
            else:
                log.error(f"[ERR] Webhook {response.status_code} → {url}: {response.text[:200]}")
        except Exception as e:
            log.error(f"[ERR] Webhook-Fehler → {url}: {e}")
    return success


def run_once(translations: dict, catalog_sections: dict, section_id_map: dict,
             force: bool = False) -> None:
    cfg = read_config()

    token, user_uuid = authenticate(cfg["email"], cfg["password"])
    if not token:
        log.error("[ERR] Login fehlgeschlagen")
        _write_status({
            "running": True, "last_error": "Login fehlgeschlagen",
            "last_push_ts": _read_state().get("last_push_ts", 0),
            "item_count": 0,
        })
        return

    shopping_list = fetch_shopping_list(token, user_uuid, cfg["list_uuid"])
    current_hash = _list_hash(shopping_list)
    state = _read_state()

    list_changed = current_hash != state["last_hash"]
    interval_elapsed = (time.time() - state["last_push_ts"]) >= cfg["webhook_interval"] * 60

    triggered = os.path.exists(TRIGGER_FILE)
    if triggered:
        try:
            os.remove(TRIGGER_FILE)
        except Exception:
            pass

    if not force and not list_changed and not interval_elapsed and not triggered:
        log.info("[--] Keine Änderung, kein Push nötig")
        _write_status({
            "running": True, "last_error": None,
            "last_push_ts": state.get("last_push_ts", 0),
            "item_count": len(shopping_list),
        })
        return

    reason = "Neustart" if force else ("Manuell" if triggered else
              ("Listenänderung" if list_changed else "Intervall abgelaufen"))
    log.info(f"[>>] Push wegen: {reason}")

    details = fetch_list_details(token, user_uuid, cfg["list_uuid"])
    details_map = {d["itemId"]: d.get("userIconItemId") or d["itemId"] for d in details}

    sections_map = {}
    for d in details:
        raw_section = d.get("userSectionId", "")
        section = section_id_map.get(raw_section, raw_section)
        sections_map[d["itemId"]] = section
        sections_map[_fix_encoding(d["itemId"])] = section

    shopping_list = sorted(
        shopping_list,
        key=lambda item: _section_rank(
            sections_map.get(item["name"]) or catalog_sections.get(item["name"], "")
        )
    )

    _write_items([
        {
            "name": item["name"],
            "display": translations.get(item["name"], item["name"]),
            "icon": resolve_icon(details_map.get(item["name"], item["name"])),
            "section": sections_map.get(item["name"]) or catalog_sections.get(item["name"], ""),
        }
        for item in shopping_list
    ])

    success = push_to_trmnl(shopping_list, translations, details_map, cfg)
    if success:
        _write_state(current_hash)

    _write_status({
        "running": True,
        "last_error": None if success else "Push fehlgeschlagen",
        "last_push_ts": time.time() if success else state.get("last_push_ts", 0),
        "item_count": len(shopping_list),
        "last_reason": reason,
    })


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    cfg = read_config()
    if not (cfg["email"] and cfg["password"] and cfg["webhook_url"]):
        log.warning("Keine vollständige Konfiguration. Bitte über die Web-Oberfläche einrichten.")
        _write_status({"running": True, "last_error": "Keine Konfiguration", "last_push_ts": 0, "item_count": 0})

    log.info("Bring! → TRMNL Dienst gestartet")

    translations = load_translations()
    log.info(f"[OK] {len(translations)} Übersetzungen geladen")
    catalog_sections, section_id_map = load_catalog_sections()
    log.info(f"[OK] {len(catalog_sections)} Katalog-Einträge geladen")

    first_run = True
    while True:
        cfg = read_config()
        poll_interval = max(cfg["poll_interval"], 1) * 60

        if cfg["email"] and cfg["password"] and cfg["webhook_url"]:
            try:
                run_once(translations, catalog_sections, section_id_map, force=first_run)
                first_run = False
            except Exception as e:
                log.error(f"[ERR] Unerwarteter Fehler: {e}")
                _write_status({"running": True, "last_error": str(e), "last_push_ts": 0, "item_count": 0})
            finally:
                gc.collect()
        else:
            log.info("[--] Warte auf Konfiguration...")

        log.info(f"[--] Nächster Abruf in {cfg['poll_interval']} Minuten")
        elapsed = 0
        while elapsed < poll_interval:
            time.sleep(10)
            elapsed += 10
            if os.path.exists(TRIGGER_FILE):
                log.info("[--] Trigger erkannt, starte sofort")
                break


if __name__ == "__main__":
    main()
