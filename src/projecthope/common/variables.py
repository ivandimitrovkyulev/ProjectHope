"""
Set up program variables.
"""
import os
from re import compile
from dotenv import load_dotenv


load_dotenv()
# Get env variables
TOKEN = os.getenv("TOKEN")
CHAT_ID_ALERTS = os.getenv("CHAT_ID_ALERTS")
CHAT_ID_ALERTS_FILTER = os.getenv("CHAT_ID_ALERTS_FILTER")
CHAT_ID_DEBUG = os.getenv("CHAT_ID_DEBUG")
BINANCE_KEY = os.getenv("BINANCE_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")


time_format = "%Y-%m-%d %H:%M:%S, %Z"

log_format = "%(asctime)s - %(levelname)s - %(message)s"
time_format_regex = compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}, [A-Za-z]*")


network_ids = {
    "1": "Ethereum",
    "56": "Binance",
    "0000": "BinanceCEX",
    "137": "Polygon",
    "10": "Optimism",
    "42161": "Arbitrum",
    "43114": "Avalanche",
    "250": "Fantom",
    "100": "Gnosis",
}

network_names = {
    "Ethereum": "1",
    "Binance": "56",
    "BinanceCEX": "0000",
    "Polygon": "137",
    "Optimism": "10",
    "Arbitrum": "42161",
    "Avalanche": "43114",
    "Fantom": "250",
    "Gnosis": "100",
}

base_tokens = ['USDC', 'USDT', 'DAI', 'BUSD']
