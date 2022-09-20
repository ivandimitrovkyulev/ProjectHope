"""
Script that starts a Binance WebSocket stream which listens for order book info for each trading pair.
Results are saved in a localhost memcached server.
"""
import os
import sys
import ast
import json
from src.projecthope.binance.api import BinanceDepthSocket


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <trading_pairs>\n")

# Construct a list of trading pairs from argument string
pairs: list = ast.literal_eval(sys.argv[-1])

# Create BinanceDepthSocket with trading pairs and start listening to streams
binance_socket = BinanceDepthSocket(pairs)
binance_socket.run_forever()
