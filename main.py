import os
import sys
import json

from atexit import register
from datetime import datetime
from time import (
    sleep,
    perf_counter,
)

from src.projecthope.common.exceptions import exit_handler
from src.projecthope.one_inch import alert_arb
from src.projecthope.common.variables import time_format


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

# Send telegram debug message if program terminates
program_name = os.path.abspath(os.path.basename(__file__))
register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
timestamp = datetime.now().astimezone().strftime(time_format)

base_token = "USDC"
base_tokens = [token for token in info['base_tokens']]
arb_tokens = [token for token in info['arb_tokens']]


print(f"{timestamp} - Started screening:")
for arb_token in arb_tokens:
    arb_token_networks = [net for net in info['arb_tokens'][arb_token]['networks']
                          if net in info['base_tokens'][base_token]['networks']]
    print(f"{arb_token} on {arb_token_networks}")


loop_counter = 1
while True:
    start = perf_counter()

    for arb_token in arb_tokens:
        alert_arb(info, base_token, arb_token)

    sleep(10)

    print(f"Loop {loop_counter} executed in {(perf_counter() - start):,.2f} secs.")
    loop_counter += 1
