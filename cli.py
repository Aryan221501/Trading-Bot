#!/usr/bin/env python3
"""
Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
Place a market order:
    python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Place a limit order:
    python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000

Place a stop-limit order (bonus order type):
    python cli.py order --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
        --quantity 0.01 --price 60000 --stop-price 60500

Run without real credentials / network access (generates realistic,
clearly-labelled simulated logs and output):
    python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run

Launch the guided interactive menu (bonus enhanced CLI UX):
    python cli.py menu
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from bot.client import BinanceFuturesTestnetClient, NetworkError, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import OrderExecutionError, execute_order
from bot.validators import ValidationError, build_order_request

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


def _load_env_file(path: str = ".env") -> None:
    """Very small .env loader (avoids adding python-dotenv as a hard
    dependency). Silently does nothing if the file does not exist."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _build_client(args, logger) -> Optional[BinanceFuturesTestnetClient]:
    if args.dry_run:
        return None

    api_key = args.api_key or os.environ.get("BINANCE_API_KEY")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Missing API credentials.")
        print(
            "ERROR: API credentials not found.\n"
            "Set BINANCE_API_KEY / BINANCE_API_SECRET (env vars or a .env file),\n"
            "pass --api-key/--api-secret, or use --dry-run to try the bot without them.",
            file=sys.stderr,
        )
        sys.exit(2)

    base_url = args.base_url or os.environ.get("BINANCE_BASE_URL", DEFAULT_BASE_URL)
    return BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


def _add_common_credential_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help="Binance Testnet API key (overrides BINANCE_API_KEY env var).")
    parser.add_argument("--api-secret", help="Binance Testnet API secret (overrides BINANCE_API_SECRET env var).")
    parser.add_argument("--base-url", help=f"API base URL (default: {DEFAULT_BASE_URL}).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the order locally without calling the exchange or needing API keys.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show DEBUG-level logs on the console too.")


def cmd_order(args) -> int:
    logger = setup_logging(verbose=args.verbose)

    try:
        order = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    client = _build_client(args, logger)

    try:
        execute_order(order, client, dry_run=args.dry_run)
    except OrderExecutionError as exc:
        logger.error("Order execution failed: %s", exc)
        return 1

    return 0


def cmd_check(args) -> int:
    """Bonus utility: verify API credentials / connectivity without
    placing an order."""
    logger = setup_logging(verbose=args.verbose)
    client = _build_client(args, logger)
    if client is None:
        print("Nothing to check in --dry-run mode (no credentials required).")
        return 0
    try:
        account = client.check_connectivity()
    except (BinanceAPIError, NetworkError) as exc:
        print(f"Connectivity check FAILED: {exc}")
        return 1
    print("Connectivity check OK. Account snapshot keys:", list(account.keys())[:10])
    return 0


def cmd_menu(args) -> int:
    """Bonus: enhanced, guided interactive CLI (menus + prompts +
    validation messages), for users who'd rather be walked through order
    entry than remember argparse flags."""
    logger = setup_logging(verbose=args.verbose)
    print("=== Binance Futures Testnet Trading Bot - Interactive Mode ===\n")

    dry_run = _prompt_yes_no("Run in dry-run mode (no real orders, no API keys needed)?", default=True)

    client = None
    if not dry_run:
        api_key = os.environ.get("BINANCE_API_KEY") or input("API key: ").strip()
        api_secret = os.environ.get("BINANCE_API_SECRET") or input("API secret: ").strip()
        base_url = os.environ.get("BINANCE_BASE_URL", DEFAULT_BASE_URL)
        try:
            client = BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1

    while True:
        symbol = input("\nSymbol (e.g. BTCUSDT): ").strip()
        side = _prompt_choice("Side", ["BUY", "SELL"])
        order_type = _prompt_choice("Order type", ["MARKET", "LIMIT", "STOP_LIMIT"])
        quantity = input("Quantity: ").strip()

        price = None
        stop_price = None
        if order_type in ("LIMIT", "STOP_LIMIT"):
            price = input("Price: ").strip()
        if order_type == "STOP_LIMIT":
            stop_price = input("Stop price (trigger): ").strip()

        try:
            order = build_order_request(
                symbol=symbol, side=side, order_type=order_type,
                quantity=quantity, price=price, stop_price=stop_price,
            )
        except ValidationError as exc:
            print(f"Invalid input: {exc}\nPlease try again.\n")
            continue

        try:
            execute_order(order, client, dry_run=dry_run)
        except OrderExecutionError as exc:
            print(f"Order failed: {exc}\n")

        if not _prompt_yes_no("Place another order?", default=False):
            break

    print("Goodbye!")
    return 0


def _prompt_choice(label: str, choices: list) -> str:
    choice_str = "/".join(choices)
    while True:
        value = input(f"{label} ({choice_str}): ").strip().upper()
        if value in choices:
            return value
        print(f"  Please enter one of: {choice_str}")


def _prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {suffix}: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer y or n.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Simplified trading bot for Binance Futures Testnet (USDT-M).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    order_parser = subparsers.add_parser("order", help="Validate and place a single order.")
    order_parser.add_argument("--symbol", required=True, help="Trading pair symbol, e.g. BTCUSDT")
    order_parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    order_parser.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type",
    )
    order_parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    order_parser.add_argument("--price", help="Limit price (required for LIMIT / STOP_LIMIT)")
    order_parser.add_argument("--stop-price", help="Trigger price (required for STOP_LIMIT)")
    order_parser.add_argument(
        "--time-in-force", default="GTC", choices=["GTC", "IOC", "FOK", "gtc", "ioc", "fok"],
        help="Time in force for LIMIT/STOP_LIMIT orders (default: GTC)",
    )
    _add_common_credential_args(order_parser)
    order_parser.set_defaults(func=cmd_order)

    check_parser = subparsers.add_parser("check", help="Verify API credentials / connectivity.")
    _add_common_credential_args(check_parser)
    check_parser.set_defaults(func=cmd_check)

    menu_parser = subparsers.add_parser("menu", help="Launch guided interactive mode.")
    menu_parser.add_argument("-v", "--verbose", action="store_true")
    menu_parser.set_defaults(func=cmd_menu)

    return parser


def main(argv=None) -> int:
    _load_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
