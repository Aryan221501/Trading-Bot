"""
Input validation for the trading bot CLI.

Keeping validation in one place (and free of any network / logging side
effects) makes it trivial to unit test and to reuse from both the argparse
CLI and the interactive menu mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


class ValidationError(Exception):
    """Raised when user-supplied order parameters are invalid."""


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

# Basic sanity pattern for a Binance-style futures symbol, e.g. BTCUSDT,
# ETHUSDT, 1000SHIBUSDT. Real symbol existence is ultimately verified by the
# exchange itself; this just filters obviously malformed input early.
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


@dataclass
class OrderRequest:
    """A validated, normalised representation of a user's order request."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "GTC"


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"'{symbol}' does not look like a valid futures symbol "
            "(expected upper-case letters/digits, e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT or STOP_LIMIT).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )
    return order_type


def validate_positive_decimal(value, field_name: str) -> Decimal:
    if value is None or value == "":
        raise ValidationError(f"{field_name} is required.")
    try:
        dec = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid number, got '{value}'.") from exc
    if dec <= 0:
        raise ValidationError(f"{field_name} must be greater than zero, got '{dec}'.")
    return dec


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
    time_in_force: str = "GTC",
) -> OrderRequest:
    """Validate all raw CLI inputs and return an immutable OrderRequest.

    Raises
    ------
    ValidationError
        If any field is missing, malformed, or inconsistent with the
        chosen order type (e.g. LIMIT without a price).
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_positive_decimal(quantity, "Quantity")

    price_dec = None
    stop_price_dec = None

    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        price_dec = validate_positive_decimal(price, "Price")

    elif order_type == "STOP_LIMIT":
        if price is None:
            raise ValidationError("Price is required for STOP_LIMIT orders.")
        if stop_price is None:
            raise ValidationError("Stop price is required for STOP_LIMIT orders.")
        price_dec = validate_positive_decimal(price, "Price")
        stop_price_dec = validate_positive_decimal(stop_price, "Stop price")

    else:  # MARKET
        if price is not None:
            raise ValidationError("Price must not be supplied for MARKET orders.")

    tif = (time_in_force or "GTC").strip().upper()
    if tif not in {"GTC", "IOC", "FOK"}:
        raise ValidationError(f"time_in_force must be one of GTC/IOC/FOK, got '{tif}'.")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price_dec,
        stop_price=stop_price_dec,
        time_in_force=tif,
    )
