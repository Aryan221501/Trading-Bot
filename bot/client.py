"""
Thin REST client for the Binance Futures Testnet (USDT-M) API.

This module intentionally avoids the ``python-binance`` package and talks
to the REST API directly with ``requests``. That keeps the dependency
footprint small and makes the exact request being sent (and therefore the
HMAC signature) fully transparent and easy to log/debug.

Reference: https://binance-docs.github.io/apidocs/testnet/en/
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger()

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response (4xx/5xx with
    a Binance error code/message payload)."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code} (HTTP {status_code}): {message}")


class NetworkError(Exception):
    """Raised for connection failures, timeouts, or DNS errors."""


class BinanceFuturesTestnetClient:
    """Minimal signed REST client for Binance USDT-M Futures Testnet.

    Only the endpoints needed by this project are implemented:
      * GET  /fapi/v2/account   (connectivity / credential check)
      * POST /fapi/v1/order     (place MARKET / LIMIT / STOP orders)
      * GET  /fapi/v1/order     (query order status)
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must both be provided.")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Low level request plumbing
    # ------------------------------------------------------------------ #
    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Attach timestamp, recvWindow, and an HMAC-SHA256 signature."""
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", RECV_WINDOW_MS)
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug("HTTP %s %s | params=%s", method, url, _redact(params))

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params if method == "GET" else None,
                data=params if method != "GET" else None,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out: %s", url, exc)
            raise NetworkError(f"Request to {url} timed out.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error calling %s: %s", url, exc)
            raise NetworkError(f"Could not connect to {url}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error calling %s: %s", url, exc)
            raise NetworkError(str(exc)) from exc

        logger.debug("HTTP %s %s -> status=%s body=%s", method, url, response.status_code, response.text)

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if not response.ok:
            code = payload.get("code") if isinstance(payload, dict) else None
            message = payload.get("msg") if isinstance(payload, dict) else str(payload)
            logger.error(
                "Binance API error on %s %s: status=%s code=%s msg=%s",
                method, path, response.status_code, code, message,
            )
            raise BinanceAPIError(response.status_code, code, message or "Unknown error")

        return payload

    # ------------------------------------------------------------------ #
    # Public endpoints used by this project
    # ------------------------------------------------------------------ #
    def check_connectivity(self) -> Dict[str, Any]:
        """Ping the account endpoint to verify API keys and connectivity."""
        logger.info("Checking connectivity / credentials against %s", self.base_url)
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """Place an order on the Futures Testnet.

        ``order_type`` here is our internal type; it is translated to the
        Binance API's ``type`` field (STOP_LIMIT -> STOP).
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }

        if order_type == "MARKET":
            params["type"] = "MARKET"
        elif order_type == "LIMIT":
            params["type"] = "LIMIT"
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP_LIMIT":
            # Binance Futures calls this order type "STOP" (stop-limit,
            # as opposed to "STOP_MARKET").
            params["type"] = "STOP"
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force
        else:
            raise ValueError(f"Unsupported order_type: {order_type}")

        logger.info(
            "Submitting %s %s order | symbol=%s qty=%s price=%s stopPrice=%s",
            order_type, side, symbol, quantity, price, stop_price,
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of params with the signature masked, for safe logging."""
    redacted = dict(params)
    if "signature" in redacted:
        redacted["signature"] = "***REDACTED***"
    return redacted
