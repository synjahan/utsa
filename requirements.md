# Telegram Forwarder

Polls an API for messages and forwards them to a Telegram bot **as your own account** (not as a bot). Supports cursor-based pagination, persistent state, user mention resolution, and flexible config via `.env` or CLI flags.

> Written with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure**
```bash
cp .env.example .env
```
Then open `.env` and fill in your values (see [Configuration](#configuration) below).

**3. Get Telegram API credentials**

Go to [my.telegram.org](https://my.telegram.org) → *API development tools* → create an app (name/URL don't matter) → copy `api_id` and `api_hash` into your `.env`.

**4. Run**
```bash
python telegram_forwarder.py
```

On first run, Telegram will ask for your phone number and send you an OTP. After that a `userbot.session` file is saved and login is automatic.

---

## Configuration

Config is read in this priority order:
1. **CLI flags** (highest priority)
2. **`.env` file**
3. **Hardcoded defaults** (lowest priority)

### Required

| `.env` key / CLI flag | Description |
|---|---|
| `TELEGRAM_API_ID` / `--telegram-api-id` | From [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` / `--telegram-api-hash` | From [my.telegram.org](https://my.telegram.org) |
| `BOT_USERNAME` / `--bot-username` | Bot or chat to message, e.g. `@mybot` |
| `API_URL` / `--api-url` | Message API endpoint to poll |
| `API_KEY` / `--api-key` | `x-api-key` header value |

### Optional

| `.env` key / CLI flag | Default | Description |
|---|---|---|
| `USER_API_URL` / `--user-api-url` | `` | User lookup base URL (`/{id}` appended) |
| `INTERVAL` / `--interval` | `5` | Poll interval in seconds |
| `LIMIT` / `--limit` | `100` | `?limit=N` per API request |
| `ID_FIELD` / `--id-field` | `id` | JSON key holding each message's ID |
| `MSG_FIELD` / `--msg-field` | auto | JSON key for message text |
| `STATE_FILE` / `--state-file` | `.last_message_id` | Cursor persistence file |
| `USER_MAP_FILE` / `--user-map-file` | `.user_map.json` | User id→name cache file |
| `SESSION_FILE` / `--session-file` | `userbot` | Telethon session file name |

### CLI example

```bash
python telegram_forwarder.py \
  --telegram-api-id 12345678 \
  --telegram-api-hash abc123 \
  --bot-username @mybot \
  --api-url https://api.example.com/messages \
  --api-key secret \
  --interval 10
```

---
## Security notes

- **Never commit `.env`** — it contains your Telegram session credentials and API keys. It is gitignored by default.
- **`userbot.session` is sensitive** — it acts as a login token for your personal Telegram account. It is also gitignored.
- Only share `.env.example` (with blank values) in the repo so others know what to fill in.
