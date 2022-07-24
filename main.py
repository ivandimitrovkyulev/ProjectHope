import os
import sys
import json

from copy import deepcopy
from pprint import pprint
from atexit import register
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from time import (
    sleep,
    perf_counter,
)
from src.projecthope.one_inch import get_swapout

from src.projecthope.common.exceptions import exit_handler
from src.projecthope.common.message import telegram_send_message
from src.projecthope.common.logger import log_arbitrage
from src.projecthope.common.variables import (
    time_format,
    CHAT_ID_ALERTS_FILTER,
)


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

# Send telegram debug message if program terminates
program_name = os.path.abspath(os.path.basename(__file__))
#register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
timestamp = datetime.now().astimezone().strftime(time_format)
print(f"{timestamp} - Started screening:\n")

tokens = [data['tokens'] for data in info.values()]
print(tokens)



network_id = "1"
from_token = ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDC", 6)
to_token = ("0x0ab87046fBb341D058F17CBC4c1133F25a20a52f", "gOHM", 18)
