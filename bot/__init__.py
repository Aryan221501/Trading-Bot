"""
trading_bot.bot
================
Core package for the Binance Futures Testnet trading bot.

Modules
-------
client.py           Thin REST wrapper around the Binance Futures Testnet API
                     (request signing, retries, error normalisation).
orders.py            Order-building / order-placement business logic
                     (MARKET, LIMIT, STOP_LIMIT).
validators.py        Pure functions that validate and normalise CLI input.
logging_config.py    Central logging configuration (console + rotating file).
"""

__version__ = "1.0.0"
