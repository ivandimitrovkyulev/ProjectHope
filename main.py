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
from src.projecthope.one_inch import check_arb
from src.projecthope.common.variables import time_format


if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <input_file>\n")

# Send telegram debug message if program terminates
program_name = os.path.abspath(os.path.basename(__file__))
register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
timestamp = datetime.now().astimezone().strftime(time_format)
print(f"{timestamp} - Started screening:")

base_token = "USDC"
arb_token = "gOHM"

loop_counter = 1
while True:
    start = perf_counter()

    check_arb(info, base_token, arb_token)
    sleep(10)

    print(f"Loop {loop_counter} executed in {(perf_counter() - start):,.2f} secs.")
    loop_counter += 1
