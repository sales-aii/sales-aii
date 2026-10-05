# Sales.aii

Windows desktop sales-automation MVP. Python 3.12+, SQLite, customtkinter GUI,
single-file PyInstaller build.

Agents discover leads, analyze them with a real AI provider, draft sales
messages, negotiate discounts and verify payments. Every outbound message
requires explicit user approval.

## Requirements

- Python 3.12+
- Windows 10/11

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Configuration

Keys live in a `.env` file. Copy the template and fill in what you need:

```bash
copy .env.example .env
```

The `.env` is read from the project root when running from source, and from
next to the executable in a packaged build. **The app starts and runs without
any keys** — unconfigured integrations report themselves as unavailable instead
of pretending to work.

### AI provider (the app's "brain")

Get a key at <https://aistudio.google.com/apikey>.

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.8-flash
AI_TIMEOUT=60
AI_MAX_RETRIES=3
```

- `AI_PROVIDER=gemini` → real Gemini calls
- `AI_PROVIDER=mock` → offline canned responses, no network, no cost
- If `AI_PROVIDER=gemini` but no key is set, the app logs a warning and falls
  back to `mock`. The Settings page always shows which provider is actually live.

Model ids: <https://ai.google.dev/gemini-api/docs/models>

### Reddit — lead discovery

Create a **script** app at <https://www.reddit.com/prefs/apps>.

```env
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=Sales.aii/1.0.0
```

Uses the documented application-only OAuth flow. Read-only; no posting or DM.

### GitHub — feature requests

Token at <https://github.com/settings/tokens> (public repo read is enough).

```env
GITHUB_TOKEN=
GITHUB_API_VERSION=2022-11-28
```

### Telegram — owner notifications only

```env
TELEGRAM_BOT_TOKEN=   # from @BotFather
TELEGRAM_CHAT_ID=     # from @userinfobot
```

Never used as a customer sales channel.

Copy the bot token **whole**. It looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` —
the `<bot_id>:` prefix is part of it. A token pasted without that prefix makes
Telegram answer a bare `404 Not Found`, so the app rejects such a value locally
and tells you the expected shape instead.

#### Connection test

**Settings > Telegram > Test Bildirimi** runs a real check against the Bot API:

1. `getMe` validates the token.
2. `sendMessage` delivers an actual message, so the chat id and the bot's write
   permission are proven, not assumed.

On success the panel shows `Telegram bağlantısı başarılı` together with the bot
username and the returned `message_id`. On failure it shows Telegram's own
`description` (for example `chat not found`), never a fake success.

Both fields are prefilled from `.env`; editing them lets you test a corrected
value without restarting. The request runs on a worker thread, so the window
stays responsive, and the button is disabled while the call is in flight.

To run the same check from the terminal (sends a real message):

```bash
python tools\test_telegram_live.py
```

### Shopier — payment verification

```env
SHOPIER_API_TOKEN=    # Personal Access Token
```

Docs: <https://developer.shopier.com/docs/creating-and-using-pats>

## Tests

```bash
python -m pytest
```

Tests run against an isolated temporary database and clear the database and
outbound-channel registry between test cases, so they never touch your real
data. No API keys required — HTTP is mocked at the transport layer.

## Build EXE

```bash
pip install pyinstaller
pyinstaller sales_aii.spec --noconfirm
```

Output: `dist/Sales.aii.exe`

`data/` and `logs/` are created next to the executable (not inside PyInstaller's
temp folder, which is deleted on exit).

## Architecture

```
config/         Settings (pydantic-settings), frozen-aware paths
database/       SQLAlchemy models + session management
repositories/   Parameterised data access
services/       Business logic: discount, negotiation, message, lead
agents/         Lead, Sales, Support, Analytics
ai/             AIManager (single AI entry point) + providers/
integrations/   Reddit, GitHub, Telegram, Shopier (+ mock/ for tests)
ui/             customtkinter app, pages, components, background tasks
```

Rules the code enforces:

- `AIManager` is the only entry point to AI; agents never call a provider directly.
- UI never runs SQL — it goes through services and repositories.
- Discount rules live in `services/discount_engine.py` only, and every AI
  suggestion is re-validated by it.
- No outbound message is marked as sent unless a registered channel actually
  delivered it.
- Platform errors raise `APIError`; they are never converted into empty results
  that look like success.
- Secrets are read from settings, sent in headers, and never logged.

### Discount rules

| Rule | Behaviour |
|---|---|
| Discount > 60% | rejected |
| `final_price < minimum_price` | rejected |
| Exactly 60% | final offer; nothing may follow it |
| Unknown / inactive discount code | rejected |
| Code percentage ≠ proposed percentage | rejected |
| AI-created discount code | impossible; codes must already exist in the DB |

## Known limitations

- **No outbound sales channel ships.** Reddit and GitHub expose no DM API to
  third-party desktop apps, and Telegram is reserved for owner notifications.
  Approving a message therefore reports "No outbound channel configured" and the
  message stays unsent rather than being falsely marked as delivered. Register a
  real sender with `MessageService.register_sender(platform, callable)` to
  enable delivery.
- Lead discovery, analysis and drafting are wired to real APIs but require the
  corresponding keys; without them the app uses mocks so the flow stays testable.
- Discount negotiation is conversational state tracking — there is no automated
  follow-up scheduling.

## Troubleshooting

**App does not start** — check `logs/sales_aii.log` next to the executable.

**"Provider 'gemini' not available"** — `GEMINI_API_KEY` is empty or missing.
The app continues on the mock provider.

**401/403 from Reddit** — check `REDDIT_USER_AGENT`; Reddit requires a
descriptive agent and rejects generic ones.

**GitHub search returns 422** — search queries include `is:issue`; a bare query
is rejected for user tokens.

**Shopier always shows pending** — a sale is only marked paid when Shopier
reports `paymentStatus: paid`. Any lookup failure is reported as an error rather
than silently pending.

**Freeze while the UI loads** — DB and AI work runs on a worker thread; if you
add a new page, use `ui.tasks.run_bg` instead of calling services directly in a
button handler.