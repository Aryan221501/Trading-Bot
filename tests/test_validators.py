"""
Unit tests for bot.validators.

Run with:  python -m pytest tests/ -v
(or, without pytest installed:  python -m unittest discover tests)
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validators import ValidationError, build_order_request


class TestMarketOrder(unittest.TestCase):
    def test_valid_market_order(self):
        order = build_order_request(
            symbol="btcusdt", side="buy", order_type="market", quantity="0.01"
        )
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.order_type, "MARKET")
        self.assertEqual(order.quantity, Decimal("0.01"))
        self.assertIsNone(order.price)

    def test_market_order_rejects_price(self):
        with self.assertRaises(ValidationError):
            build_order_request(
                symbol="BTCUSDT", side="BUY", order_type="MARKET",
                quantity="0.01", price="10000",
            )


class TestLimitOrder(unittest.TestCase):
    def test_valid_limit_order(self):
        order = build_order_request(
            symbol="ETHUSDT", side="SELL", order_type="LIMIT",
            quantity="1", price="3500.5",
        )
        self.assertEqual(order.price, Decimal("3500.5"))
        self.assertEqual(order.time_in_force, "GTC")

    def test_limit_order_requires_price(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="ETHUSDT", side="SELL", order_type="LIMIT", quantity="1")


class TestStopLimitOrder(unittest.TestCase):
    def test_valid_stop_limit_order(self):
        order = build_order_request(
            symbol="BTCUSDT", side="SELL", order_type="STOP_LIMIT",
            quantity="0.02", price="60000", stop_price="60500",
        )
        self.assertEqual(order.stop_price, Decimal("60500"))

    def test_stop_limit_requires_stop_price(self):
        with self.assertRaises(ValidationError):
            build_order_request(
                symbol="BTCUSDT", side="SELL", order_type="STOP_LIMIT",
                quantity="0.02", price="60000",
            )


class TestFieldValidation(unittest.TestCase):
    def test_invalid_symbol(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="", side="BUY", order_type="MARKET", quantity="1")

    def test_invalid_side(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="BTCUSDT", side="HOLD", order_type="MARKET", quantity="1")

    def test_invalid_order_type(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="BTCUSDT", side="BUY", order_type="ICEBERG", quantity="1")

    def test_negative_quantity(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="-1")

    def test_non_numeric_quantity(self):
        with self.assertRaises(ValidationError):
            build_order_request(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="abc")

    def test_invalid_time_in_force(self):
        with self.assertRaises(ValidationError):
            build_order_request(
                symbol="BTCUSDT", side="BUY", order_type="LIMIT",
                quantity="1", price="100", time_in_force="XYZ",
            )


if __name__ == "__main__":
    unittest.main()
