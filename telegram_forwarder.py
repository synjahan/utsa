#!/usr/bin/env python3
"""
telegram_forwarder.py
---------------------
Polls an API endpoint for messages and sends them TO a Telegram bot
as if YOU typed them (uses your personal Telegram account via Telethon).

Written with the assistance of Claude (Anthropic) — https://claude.ai

Setup:
  pip install -r requirements.txt
  cp .env.example .env        # then fill in your values
  python telegram_forwarder.py

Config priority (highest → lowest):
  1. CLI arguments  (--api-key "..." etc.)
  2. .env file      (API_KEY=... etc.)
  3. Defaults       (hardcoded fallbacks for non-sensitive settings)

Get TELEGRAM_API_ID and TELEGRAM_API_HASH from:
  https://my.telegram.org → "API development tools"
On first run you'll be prompted for your phone number + Telegram OTP.
After that a session file is saved and login is automatic.
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from telethon import TelegramClient

# ── Load .env file (safe — .env is gitignored) ────────────────────────────────
load_dotenv()


# ── CLI arguments ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Forward API messages to Telegram as yourself.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Sensitive — no hardcoded defaults, must come from .env or CLI
    p.add_argument("--telegram-api-id",   default=None, help="Telegram API ID (env: TELEGRAM_API_ID)")
    p.add_argument("--telegram-api-hash", default=None, help="Telegram API hash (env: TELEGRAM_API_HASH)")
    p.add_argument("--bot-username",      default=None, help="Bot/chat to message, e.g. @mybot (env: BOT_USERNAME)")
    p.add_argument("--api-key",           default=None, help="x-api-key header value (env: API_KEY)")
    p.add_argument("--api-url",           default=None, help="Message API endpoint to poll (env: API_URL)")
    p.add_argument("--user-api-url",      default=None, help="User lookup base URL, /{id} appended (env: USER_API_URL)")

    # Non-sensitive — have sensible defaults
    p.add_argument("--interval",     type=float, default=None, help="Poll interval in seconds (env: INTERVAL, default: 5)")
    p.add_argument("--limit",        type=int,   default=None, help="?limit=N per request (env: LIMIT, default: 100)")
    p.add_argument("--id-field",     default=None, help="JSON key for message ID (env: ID_FIELD, default: id)")
    p.add_argument("--msg-field",    default=None, help="JSON key for message text, auto-detected if omitted (env: MSG_FIELD)")
    p.add_argument("--state-file",   default=None, help="Cursor persistence file (env: STATE_FILE, default: .last_message_id)")
    p.add_argument("--user-map-file",default=None, help="User map persistence file (env: USER_MAP_FILE, default: .user_map.json)")
    p.add_argument("--session-file", default=None, help="Telethon session file name (env: SESSION_FILE, default: userbot)")

    return p.parse_args()


def resolve_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Merge config: CLI args override .env, .env overrides hardcoded defaults.
    For each value: use CLI arg if given, else .env, else default.
    """
    def get(cli_val, env_key, default=None):
        if cli_val is not None:
            return cli_val
        env_val = os.getenv(env_key)
        if env_val is not None:
            return env_val
        return default

    return {
        # Sensitive
        "TELEGRAM_API_ID":   int(get(args.telegram_api_id,   "TELEGRAM_API_ID",   0)),
        "TELEGRAM_API_HASH": get(args.telegram_api_hash,      "TELEGRAM_API_HASH", ""),
        "BOT_USERNAME":      get(args.bot_username,           "BOT_USERNAME",      ""),
        "API_KEY":           get(args.api_key,                "API_KEY",           ""),
        "API_URL":           get(args.api_url,                "API_URL",           ""),
        "USER_API_URL":      get(args.user_api_url,           "USER_API_URL",      ""),
        # Non-sensitive
        "INTERVAL":      float(get(args.interval,      "INTERVAL",      5.0)),
        "LIMIT":         int(get(args.limit,           "LIMIT",         100)),
        "ID_FIELD":      get(args.id_field,            "ID_FIELD",      "id"),
        "MSG_FIELD":     get(args.msg_field,           "MSG_FIELD",     None) or None,
        "STATE_FILE":    get(args.state_file,          "STATE_FILE",    ".last_message_id"),
        "USER_MAP_FILE": get(args.user_map_file,       "USER_MAP_FILE", ".user_map.json"),
        "SESSION_FILE":  get(args.session_file,        "SESSION_FILE",  "userbot"),
    }


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Persistent cursor ─────────────────────────────────────────────────────────

def load_last_id(state_file: Path) -> Optional[str]:
    try:
        text = state_file.read_text().strip()
        return text if text else None
    except FileNotFoundError:
        return None


def save_last_id(state_file: Path, message_id: str) -> None:
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(message_id)
    tmp.replace(state_file)
    log.debug("Cursor saved → %s", message_id)


# ── API polling ───────────────────────────────────────────────────────────────

def poll_api(api_url: str, api_key: str, after: Optional[str], limit: int) -> Optional[Any]:
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    params: Dict[str, Any] = {"limit": limit}
    if after:
        params["after"] = after
    try:
        r = requests.get(api_url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        log.debug("GET %s  →  %d", r.url, r.status_code)
        return r.json()
    except requests.exceptions.JSONDecodeError:
        return r.text if r.ok else None
    except requests.RequestException as exc:
        log.error("API poll failed: %s", exc)
        return None


# ── Message extraction ────────────────────────────────────────────────────────

def extract_items(data: Any, msg_field: Optional[str]) -> List[Dict]:
    items: List[Any] = []
    if isinstance(data, str):
        items = [data]
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if msg_field and msg_field in data:
            value = data[msg_field]
            items = value if isinstance(value, list) else [value]
        else:
            for key in ("messages", "data", "items", "results", "content"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                for key in ("message", "text"):
                    if key in data:
                        items = [data]
                        break
                else:
                    items = [data]
    return [{"text": i} if isinstance(i, str) else i for i in items if i]


def item_id(item: Dict, id_field: str) -> Optional[str]:
    val = item.get(id_field)
    return str(val) if val is not None else None


# ── User map ──────────────────────────────────────────────────────────────────

user_map: Dict[str, Dict[str, str]] = {}


def load_user_map(user_map_file: str) -> None:
    global user_map
    try:
        user_map = json.loads(Path(user_map_file).read_text())
        log.info("Loaded %d user(s) from %s", len(user_map), user_map_file)
    except FileNotFoundError:
        user_map = {}
        log.info("No user map file found — starting fresh")
    except Exception as exc:
        log.warning("Could not load user map: %s", exc)
        user_map = {}


def save_user_map(user_map_file: str) -> None:
    tmp = Path(user_map_file).with_suffix(".tmp")
    tmp.write_text(json.dumps(user_map, indent=2))
    tmp.replace(Path(user_map_file))
    log.debug("User map saved (%d users)", len(user_map))


def update_user_map(item: Dict) -> bool:
    author = item.get("author") or {}
    author_id = author.get("id")
    if not author_id:
        return False
    entry = {
        "displayName": author.get("displayName") or "",
        "username":    author.get("username") or "",
    }
    if user_map.get(author_id) != entry:
        user_map[author_id] = entry
        return True
    return False


def fetch_user(uid: str, user_api_url: str, api_key: str) -> Optional[Dict[str, str]]:
    url = "{}/users/{}".format(user_api_url.rstrip("/"), uid)
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        user = r.json().get("user") or {}
        if user.get("id"):
            entry = {
                "displayName": user.get("displayName") or "",
                "username":    user.get("username") or "",
            }
            log.info("Fetched unknown user %s → %s", uid, entry.get("displayName") or entry.get("username"))
            return entry
    except Exception as exc:
        log.warning("Could not fetch user %s: %s", uid, exc)
    return None


def resolve_mentions(content: str, user_api_url: str, api_key: str, user_map_file: str) -> str:
    def replacer(match):
        uid = match.group(1)
        if uid not in user_map:
            entry = fetch_user(uid, user_api_url, api_key)
            if entry:
                user_map[uid] = entry
                save_user_map(user_map_file)
        if uid in user_map:
            name = user_map[uid].get("displayName") or user_map[uid].get("username") or uid
            return "@{}".format(name)
        return match.group(0)
    return re.sub(r'<@(\d{17,19})>', replacer, content)


def item_text(item: Dict, msg_field: Optional[str], user_api_url: str, api_key: str, user_map_file: str) -> Optional[str]:
    content = (item.get("content") or "").strip()
    created = item.get("createdAt", "")
    author  = item.get("author") or {}
    display = author.get("displayName") or author.get("username") or "Unknown"

    if not content:
        return None

    content = resolve_mentions(content, user_api_url, api_key, user_map_file)

    if created:
        created = created[:19].replace("T", " ")

    if created:
        return "{} - {}: {}".format(display, created, content)
    return "{}: {}".format(display, content)


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run(client: TelegramClient, cfg: Dict[str, Any]) -> None:
    state_file = Path(cfg["STATE_FILE"])
    last_id = load_last_id(state_file)
    load_user_map(cfg["USER_MAP_FILE"])

    if last_id:
        log.info("Resuming from message ID %s", last_id)
    else:
        log.info("No saved cursor — fetching latest %d messages on first run", cfg["LIMIT"])

    log.info("Sending messages as YOU to %s", cfg["BOT_USERNAME"])
    log.info("Polling %s every %.1fs", cfg["API_URL"], cfg["INTERVAL"])

    while True:
        data = poll_api(cfg["API_URL"], cfg["API_KEY"], after=last_id, limit=cfg["LIMIT"])

        if data is None:
            log.warning("No data received from API this cycle")
            await asyncio.sleep(cfg["INTERVAL"])
            continue

        new_last_id: Optional[str] = None
        if isinstance(data, dict):
            cursors = data.get("cursors") or {}
            new_last_id = cursors.get("latest") or None

        items = list(reversed(extract_items(data, cfg["MSG_FIELD"])))

        if not items:
            log.debug("No new messages")
            if new_last_id:
                save_last_id(state_file, new_last_id)
                last_id = new_last_id
            await asyncio.sleep(cfg["INTERVAL"])
            continue

        log.info("Received %d message(s) from API", len(items))

        # Pass 1: build full user map for this batch before sending
        map_changed = False
        for item in items:
            if update_user_map(item):
                map_changed = True
        if map_changed:
            save_user_map(cfg["USER_MAP_FILE"])

        # Pass 2: format and send
        for item in items:
            msg_id = item_id(item, cfg["ID_FIELD"])
            text   = item_text(item, cfg["MSG_FIELD"], cfg["USER_API_URL"], cfg["API_KEY"], cfg["USER_MAP_FILE"])

            if text is None:
                log.debug("Skipped [id=%s]: no text content", msg_id or "?")
                continue

            try:
                await client.send_message(cfg["BOT_USERNAME"], text)
                preview = text[:80] + ("..." if len(text) > 80 else "")
                log.info("Sent [id=%s]: %s", msg_id or "?", preview)
            except Exception as exc:
                log.error("Failed to send message: %s", exc)

        if new_last_id:
            save_last_id(state_file, new_last_id)
            last_id = new_last_id
            log.debug("Cursor updated → %s", last_id)

        await asyncio.sleep(cfg["INTERVAL"])


async def main() -> None:
    args = parse_args()
    cfg  = resolve_config(args)

    missing = [
        name for name, val in [
            ("TELEGRAM_API_ID",   cfg["TELEGRAM_API_ID"]),
            ("TELEGRAM_API_HASH", cfg["TELEGRAM_API_HASH"]),
            ("BOT_USERNAME",      cfg["BOT_USERNAME"]),
            ("API_URL",           cfg["API_URL"]),
            ("API_KEY",           cfg["API_KEY"]),
        ] if not val
    ]
    if missing:
        print("ERROR: missing required config. Set in .env or pass as CLI args:\n  " + "\n  ".join(missing))
        sys.exit(1)

    async with TelegramClient(cfg["SESSION_FILE"], cfg["TELEGRAM_API_ID"], cfg["TELEGRAM_API_HASH"]) as client:
        log.info("Logged in as: %s", (await client.get_me()).username)
        try:
            await run(client, cfg)
        except KeyboardInterrupt:
            log.info("Stopped by user.")


if __name__ == "__main__":
    asyncio.run(main())
