import re
import requests
from typing import Dict, List, Optional, Tuple

_icon_exists_cache: Dict[str, bool] = {}

BASE_URL = "https://api.getbring.com/rest/v2/bringlists"
LOGIN_URL = "https://api.getbring.com/rest/v2/bringauth"
USERS_URL = "https://api.getbring.com/rest/v2/bringusers"
TRANSLATIONS_URL = "https://web.getbring.com/locale/articles.de-AT.json"
CATALOG_URL = "https://web.getbring.com/locale/catalog.de-AT.json"
ICON_BASE_URL = "https://web.getbring.com/assets/images/items/"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-BRING-API-KEY": "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp",
    "X-BRING-CLIENT": "webApp",
    "X-BRING-COUNTRY": "de",
    "X-BRING-VERSION": "303070050",
}


def _icon_exists(filename: str) -> bool:
    if filename not in _icon_exists_cache:
        try:
            r = requests.head(f"{ICON_BASE_URL}{filename}", timeout=5)
            _icon_exists_cache[filename] = r.status_code == 200
        except Exception:
            _icon_exists_cache[filename] = False
    return _icon_exists_cache[filename]


def resolve_icon(icon_name: str) -> str:
    normalized = normalize(icon_name)
    if not normalized:
        return "a.png"
    filename = f"{normalized}.png"
    if _icon_exists(filename):
        return filename
    return f"{normalized[0]}.png"


def normalize(name: str) -> str:
    result = name.lower()
    for old, new in [(" ", "_"), ("-", "_"), ("!", ""), ("ä", "ae"), ("ö", "oe"), ("ü", "ue"),
                     ("é", "e"), ("è", "e"), ("à", "a"), ("ß", "ss"), ("Ä", "ae"), ("Ö", "oe"),
                     ("Ü", "ue"), ("&", "und"), ("+", "plus")]:
        result = result.replace(old, new)
    return re.sub(r"[^a-z0-9_]", "", result)


def authenticate(email: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    response = requests.post(LOGIN_URL, data={"email": email, "password": password}, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token"), data.get("uuid")
    return None, None


def fetch_all_lists(token: str, user_uuid: str) -> List[dict]:
    headers = {**HEADERS, "Authorization": f"Bearer {token}", "X-BRING-USER-UUID": user_uuid}
    response = requests.get(f"{USERS_URL}/{user_uuid}/lists", headers=headers)
    if response.status_code == 200:
        return response.json().get("lists", [])
    return []


def fetch_shopping_list(token: str, user_uuid: str, list_uuid: str) -> List[dict]:
    headers = {**HEADERS, "Authorization": f"Bearer {token}", "X-BRING-USER-UUID": user_uuid}
    response = requests.get(f"{BASE_URL}/{list_uuid}", headers=headers)
    if response.status_code == 200:
        return response.json().get("purchase", [])
    return []


def fetch_list_details(token: str, user_uuid: str, list_uuid: str) -> List[dict]:
    headers = {**HEADERS, "Authorization": f"Bearer {token}", "X-BRING-USER-UUID": user_uuid}
    response = requests.get(f"{BASE_URL}/{list_uuid}/details", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []


def load_catalog_sections() -> tuple:
    """Returns ({itemId: section_name}, {sectionId: section_name}) from the Bring! catalog."""
    try:
        response = requests.get(CATALOG_URL, timeout=10)
        if response.status_code == 200:
            items_map: Dict[str, str] = {}
            id_map: Dict[str, str] = {}
            for section in response.json().get("catalog", {}).get("sections", []):
                section_id = section.get("sectionId", "")
                name = section.get("name", "")
                id_map[section_id] = name
                for item in section.get("items", []):
                    items_map[item["itemId"]] = name
            return items_map, id_map
    except Exception:
        pass
    return {}, {}


def load_translations() -> Dict[str, str]:
    try:
        response = requests.get(TRANSLATIONS_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}
