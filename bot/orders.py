"""
Order placement logic: bridges validated ``OrderRequest`` objects to the
Binance client, and prints/logs a clean summary of what was requested and
what the exchange responded with.

A ``dry_run`` mode is included so the bot (and its logging) can be
exercised end-to-end without live API credentials or a network
connection -- this is what generates the example log entries shipped in
``logs/`` for the assignment deliverables. In dry-run mode no network
call is made; a realistic, clearly-labelled simulated response is
produced instead.
"""

from __future__ import annotations

import random
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from .client import BinanceAPIError, BinanceFuturesTestnetClient, NetworkError
from .logging_config import get_logger
from .validators import OrderRequest

logger = get_logger()


class OrderExecutionError(Exception):
    """Raised when an order could not be placed, wrapping the root cause."""


def _print_request_summary(order: OrderRequest) -> None:
    print("\n=== Order Request ===")
    print(f"  Symbol      : {order.symbol}")
    print(f"  Side        : {order.side}")
    print(f"  Type        : {order.order_type}")
    print(f"  Quantity    : {order.quantity}")
    if order.price is not None:
        print(f"  Price       : {order.price}")
    if order.stop_price is not None:
        print(f"  Stop Price  : {order.stop_price}")
    if order.order_type != "MARKET":
        print(f"  TimeInForce : {order.time_in_force}")
    print("======================\n")


def _print_response_summary(response: Dict[str, Any]) -> None:
    print("=== Order Response ===")
    print(f"  Order ID     : {response.get('orderId')}")
    print(f"  Status       : {response.get('status')}")
    print(f"  Executed Qty : {response.get('executedQty', 'N/A')}")
    avg_price = response.get("avgPrice")
    if avg_price is not None:
        print(f"  Avg Price    : {avg_price}")
    print("=======================\n")


def _simulate_response(order: OrderRequest) -> Dict[str, Any]:
    """Build a realistic mock exchange response for dry-run mode.

    The shape mirrors Binance's real /fapi/v1/order response fields so the
    rest of the pipeline (printing + logging) is exercised identically to
    the live path.
    """
    order_id = random.randint(10_000_000, 99_999_999)
    filled = order.order_type == "MARKET"
    sim_price = order.price if order.price is not None else "68000.00"

    return {
        "orderId": order_id,
        "symbol": order.symbol,
        "status": "FILLED" if filled else "NEW",
        "side": order.side,
        "type": order.order_type if order.order_type != "STOP_LIMIT" else "STOP",
        "origQty": str(order.quantity),
        "executedQty": str(order.quantity) if filled else "0",
        "avgPrice": str(sim_price) if filled else "0",
        "price": str(order.price) if order.price is not None else "0",
        "timeInForce": order.time_in_force,
        "updateTime": int(time.time() * 1000),
        "_simulated": True,
    }


def execute_order(
    order: OrderRequest,
    client: Optional[BinanceFuturesTestnetClient],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Validate-then-place an order, printing and logging a full audit trail.

    Parameters
    ----------
    order:
        A pre-validated :class:`~bot.validators.OrderRequest`.
    client:
        A configured :class:`BinanceFuturesTestnetClient`. May be ``None``
        only when ``dry_run=True``.
    dry_run:
        If True, no network call is made; a simulated response is
        generated and clearly marked as such in both stdout and the logs.

    Returns
    -------
    dict
        The (real or simulated) order response payload from the exchange.

    Raises
    ------
    OrderExecutionError
        If the API call fails (validation errors should be caught by the
        caller *before* this function is invoked, via ``build_order_request``).
    """
    logger.info("Preparing order: %s", asdict(order))
    _print_request_summary(order)

    if dry_run:
        logger.warning("DRY-RUN mode enabled: no real API call will be made.")
        response = _simulate_response(order)
        logger.info("Simulated order response: %s", response)
        print("*** DRY RUN: this is a simulated response, no real order was placed ***\n")
        _print_response_summary(response)
        print("Result: SUCCESS (simulated)\n")
        return response

    if client is None:
        raise OrderExecutionError("A configured API client is required when dry_run=False.")

    try:
        response = client.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=str(order.quantity),
            price=str(order.price) if order.price is not None else None,
            stop_price=str(order.stop_price) if order.stop_price is not None else None,
            time_in_force=order.time_in_force,
        )
    except BinanceAPIError as exc:
        logger.error("Order rejected by exchange: %s", exc)
        print(f"Result: FAILED - exchange rejected the order ({exc.message})\n")
        raise OrderExecutionError(str(exc)) from exc
    except NetworkError as exc:
        logger.error("Order failed due to network error: %s", exc)
        print(f"Result: FAILED - network error ({exc})\n")
        raise OrderExecutionError(str(exc)) from exc

    logger.info("Order accepted by exchange: %s", response)
    _print_response_summary(response)
    print("Result: SUCCESS\n")
    return response
