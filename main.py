import os
import sys
import json

from atexit import register
from datetime import datetime
from time import (
    sleep,
    perf_counter,
)
from concurrent.futures import ThreadPoolExecutor

from src.projecthope.common.exceptions import exit_handler
from src.projecthope.one_inch.api import alert_arb
from src.projecthope.common.variables import time_format
from src.projecthope.common.helpers import print_start_message


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

# Send telegram debug message if program terminates
program_name = os.path.abspath(os.path.basename(__file__))
register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
timestamp = datetime.now().astimezone().strftime(time_format)

base_token = "USDC"
arb_tokens = [token for token in info['arb_tokens']]

print_start_message(info, base_token, timestamp)


loop_counter = 1
while True:
    start = perf_counter()

    arguments = [[info, base_token, arb_token] for arb_token in arb_tokens]
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = pool.map(lambda p: alert_arb(*p), arguments, timeout=10)

    sleep(10)

    print(f"Loop {loop_counter} executed in {(perf_counter() - start):,.2f} secs.")
    loop_counter += 1
