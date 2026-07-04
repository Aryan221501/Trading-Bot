"""
Tests for bot.orders using dry_run mode so no network access or API keys
are required.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.orders import execute_order
from bot.validators import build_order_request


class TestDryRunExecution(unittest.TestCase):
    def test_market_order_dry_run_fills_immediately(self):
        order = build_order_request(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.01")
        response = execute_order(order, client=None, dry_run=True)
        self.assertTrue(response["_simulated"])
        self.assertEqual(response["status"], "FILLED")
        self.assertEqual(response["executedQty"], "0.01")

    def test_limit_order_dry_run_stays_new(self):
        order = build_order_request(
            symbol="BTCUSDT", side="SELL", order_type="LIMIT", quantity="0.02", price="70000"
        )
        response = execute_order(order, client=None, dry_run=True)
        self.assertTrue(response["_simulated"])
        self.assertEqual(response["status"], "NEW")
        self.assertEqual(response["price"], "70000")

    def test_execute_without_client_and_without_dry_run_raises(self):
        order = build_order_request(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.01")
        with self.assertRaises(Exception):
            execute_order(order, client=None, dry_run=False)


if __name__ == "__main__":
    unittest.main()
