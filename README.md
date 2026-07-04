# Binance Futures Testnet Trading Bot

A small, well-structured Python CLI application that places **MARKET**,
**LIMIT**, and **STOP_LIMIT** (bonus) orders on **Binance Futures Testnet
(USDT-M)**, with input validation, structured logging, and clean
request/response reporting.

Built for the *Python Developer Intern* application task.

---

## Features

- Places **Market** and **Limit** orders, both **BUY** and **SELL**, on
  Binance Futures Testnet (USDT-M).
- **Bonus order type:** `STOP_LIMIT` (mapped to Binance's `STOP` futures
  order type — a stop-triggered limit order).
- CLI input validation via `argparse` (symbol, side, order type,
  quantity, price / stop price where required).
- Clean printed output: request summary, response details (order ID,
  status, executed quantity, average price), and a clear success/failure
  message.
- **Structured code**: API/client layer (`bot/client.py`) is fully
  separated from order logic (`bot/orders.py`), validation
  (`bot/validators.py`), and the CLI layer (`cli.py`).
- **Logging**: every request, response, and error is written to a
  rotating log file at `logs/trading_bot.log`, with a shorter view
  mirrored to the console.
- **Exception handling** for invalid input, API errors (bad symbol,
  insufficient balance, etc.), and network failures (timeouts, DNS,
  connection errors).
- **Bonus enhanced UX:** a guided interactive `menu` mode with prompts
  and inline validation messages, in addition to the scriptable
  `order` subcommand.
- **`--dry-run` mode:** exercises the entire pipeline (validation →
  request build → logging → response handling) with a simulated
  exchange response, so the bot can be tried out and its logging
  demonstrated without live API keys or network access. This is how the
  sample log entries in `logs/trading_bot.log` were produced.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance Futures Testnet REST client (signing, HTTP, errors)
│   ├── orders.py           # Order placement logic + dry-run simulation
│   ├── validators.py       # CLI input validation → OrderRequest
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                  # CLI entry point (order / check / menu subcommands)
├── tests/
│   ├── test_validators.py  # Unit tests for input validation
│   └── test_orders.py      # Unit tests for order execution (dry-run)
├── logs/
│   └── trading_bot.log     # Sample logs (1 MARKET, 1 LIMIT, 1 STOP_LIMIT, 1 error)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.9+
- A Binance Futures **Testnet** account with API credentials (only
  needed for live calls — see [Dry-run mode](#dry-run-mode) to try the
  bot without them):
  1. Go to <https://testnet.binancefuture.com> and log in with a GitHub
     account.
  2. Generate an API key/secret pair from the testnet dashboard.
  3. Fund your testnet futures wallet with the free test USDT provided.

### 2. Install dependencies

```bash
cd trading_bot
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows Command Prompt: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

On Windows, prefer creating the virtual environment with the standard
Python launcher so the activation script lands in the usual
`.venv\\Scripts` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If the environment was created with MSYS2 or another Unix-style Python
build, the activation script may be in `.venv\\bin\\Activate.ps1`
instead.

The only runtime dependency is `requests`; the API client talks to the
REST API directly (with manual HMAC-SHA256 request signing) rather than
depending on the `python-binance` package, so the exact request being
signed and sent is fully transparent.

### 3. Configure credentials

```bash
cp .env.example .env
# then edit .env and paste in your testnet API key/secret
```

`cli.py` auto-loads `.env` on startup. Credentials can also be passed
via environment variables (`BINANCE_API_KEY`, `BINANCE_API_SECRET`) or
CLI flags (`--api-key`, `--api-secret`), which take priority.

---

## How to Run

### Place a Market order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Place a Limit order

```bash
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000
```

### Place a Stop-Limit order (bonus order type)

```bash
python cli.py order --symbol BTCUSDT --side SELL --type STOP_LIMIT \
    --quantity 0.01 --price 60000 --stop-price 60500
```

`--stop-price` is the trigger price; `--price` is the limit price the
order rests at once triggered.

### Check connectivity / credentials

```bash
python cli.py check
```

### Dry-run mode

Try the full pipeline — validation, logging, request/response
formatting — without real API keys or network access:

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

The response is clearly labelled `_simulated: true` in the logs and
`*** DRY RUN ***` on screen, so simulated and live runs are never
ambiguous.

### Guided interactive mode (bonus UX)

```bash
python cli.py menu
```

Walks you through symbol / side / order type / quantity / price with
inline validation and a yes/no loop to place multiple orders in one
session.

### Verbose logging

Add `-v` / `--verbose` to any command to also print DEBUG-level logs
(raw request/response payloads) to the console. The log **file** always
captures DEBUG and above regardless of this flag.

---

## Example output

```
=== Order Request ===
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.01
======================

=== Order Response ===
  Order ID     : 28511234
  Status       : FILLED
  Executed Qty : 0.01
  Avg Price    : 68000.00
=======================

Result: SUCCESS
```

## Logging

All activity is written to `logs/trading_bot.log` (rotated at 1MB, 5
backups kept). Sample entries for one MARKET, one LIMIT, and one
STOP_LIMIT order (plus a validation error) are already included in that
file so you can inspect the log format without running anything.

Log line format:

```
<timestamp> | <LEVEL> | trading_bot | <message>
```

- `INFO` — order lifecycle events (request prepared, response received)
- `WARNING` — dry-run notices, recoverable conditions
- `ERROR` — validation failures, rejected orders, network errors
- `DEBUG` — raw HTTP request/response payloads (file only, unless `-v`)

## Running tests

```bash

python -m unittest discover tests -v
```

Tests cover input validation (valid/invalid MARKET, LIMIT, STOP_LIMIT
orders, bad symbols/sides/quantities) and order execution in dry-run
mode, so they run without any network access or API credentials.

## Troubleshooting

- `401` / `-2015` (`Invalid API-key, IP, or permissions for action`):
  the testnet rejected the credentials or account permissions for the
  signed request. Check that `BINANCE_API_KEY` and
  `BINANCE_API_SECRET` are loaded from the intended `.env` file, that
  you are using the **testnet** API key pair (not mainnet), and that the
  key has futures permissions enabled on the Binance testnet dashboard.
- If you are using IP restrictions on the API key, make sure the current
  machine's public IP is allowed.
- Run `python cli.py check` first to verify the credentials before
  placing an order. If you only want to validate the CLI locally, use
  `--dry-run` so no exchange request is sent.

---

## Assumptions

- **REST calls over `python-binance`:** the client is implemented with
  `requests` and manual HMAC-SHA256 signing rather than the
  `python-binance` library, to keep the dependency surface minimal and
  the signed request fully visible/loggable.
- **`STOP_LIMIT` → Binance `STOP`:** Binance Futures' native order type
  for a stop-triggered limit order is called `STOP` (as opposed to
  `STOP_MARKET`). The CLI exposes it under the clearer name
  `STOP_LIMIT` and translates it internally.
- **Testnet only:** the base URL is hard-coded to
  `https://testnet.binancefuture.com` by default; it can be overridden
  with `--base-url` / `BINANCE_BASE_URL` if needed, but this project is
  not intended for mainnet use.
- **No `python-dotenv` dependency:** `.env` loading is implemented with
  a small built-in parser (`cli.py:_load_env_file`) to keep
  `requirements.txt` to a single package.
- **Sample logs are simulated:** this sandboxed development environment
  has no outbound network access to `testnet.binancefuture.com`, so the
  committed `logs/trading_bot.log` was generated with `--dry-run`
  (clearly marked `_simulated: true`) rather than a live testnet call.
  The exact same code path (`bot/orders.py:execute_order`) handles both
  simulated and live responses — running any `order` command without
  `--dry-run` and with valid testnet credentials appends real
  request/response log entries in the identical format.
- **`recvWindow`** defaults to 5000ms and quantity/price precision
  (`LOT_SIZE` / `PRICE_FILTER`) is not pre-validated against exchange
  filters client-side; Binance will reject and the bot will surface and
  log the exchange's specific error message (e.g. `"Filter failure:
  LOT_SIZE"`) rather than silently rounding.

---

## Evaluation checklist (from the assignment)

- [x] Places Market and Limit orders on Futures Testnet (USDT-M)
- [x] Supports BUY and SELL
- [x] CLI input validation (argparse)
- [x] Clear request/response/success-failure output
- [x] Separate client/API layer and CLI layer
- [x] Logging of requests, responses, and errors to a log file
- [x] Exception handling: invalid input, API errors, network failures
- [x] README with setup, run examples, assumptions
- [x] requirements.txt
- [x] Sample logs for one MARKET and one LIMIT order
- [x] Bonus: third order type (STOP_LIMIT)
- [x] Bonus: enhanced CLI UX (`menu` interactive mode)
